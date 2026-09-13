"""
相机标定工具（功能一·相机畸变矫正）。

拍/读棋盘格图 -> 检测角点 -> cv2.calibrateCamera 算内参与畸变系数
-> 存 pkl / 做畸变校正。

- 从图片目录标定的路径（load_images_from_directory / calibrate_camera /
  save_calibration / undistort_image）完全不依赖相机 SDK。
- 只有实时采集（capture_calibration_images / initialize_camera /
  cleanup_camera）才需要 mvsdk + 实体相机，均为函数内懒加载。

标定 pkl 的读写集中在模块级 load_calibration_data / save_calibration_data，
供本工具与 tools/scale.py 共用，避免字段契约散落多处。
"""

import sys
import argparse
import numpy as np
import cv2
import os
import glob
import pickle
from datetime import datetime
from pathlib import Path

# 使 src / config / libs 包可被导入
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# 标定数据 pkl 读写（单一来源）

def load_calibration_data(filename="camera_calibration.pkl"):
    """
    读取相机标定 pkl 并返回原始字典（pkl 字段读取的唯一入口）。

    Args:
        filename: 标定文件路径

    Returns:
        dict: 标定数据；至少包含 camera_matrix / dist_coeffs / img_size

    Raises:
        底层异常（FileNotFoundError / pickle 错误等）由调用方按需处理。
    """
    with open(filename, 'rb') as f:
        return pickle.load(f)


def save_calibration_data(calibration_data, filename="camera_calibration.pkl"):
    """
    将标定数据字典写入 pkl（pkl 字段写入的唯一入口）。

    Args:
        calibration_data: 标定数据字典
        filename: 保存文件路径

    Returns:
        bool: 是否保存成功
    """
    try:
        with open(filename, 'wb') as f:
            pickle.dump(calibration_data, f)
        return True
    except Exception as e:
        print(f"保存失败: {e}")
        return False


class CameraCalibrator:
    def __init__(self, checkerboard_size=(10, 7), square_size=18.0):
        """
        初始化相机标定类

        Args:
            checkerboard_size: 棋盘内角点数量 (列, 行)，默认 (10, 7)
            square_size: 棋盘方格的实际尺寸(mm)，默认 18.0
        """
        self.checkerboard_size = checkerboard_size
        self.square_size = square_size

        # 准备标定板的3D点
        self.objp = np.zeros((checkerboard_size[0] * checkerboard_size[1], 3), np.float32)
        self.objp[:, :2] = np.mgrid[0:checkerboard_size[0], 0:checkerboard_size[1]].T.reshape(-1, 2)
        self.objp *= square_size

        # 存储3D点和2D点的数组
        self.objpoints = []  # 真实世界中的3D点
        self.imgpoints = []  # 图像中的2D点

        # 标定结果
        self.camera_matrix = None
        self.dist_coeffs = None
        self.rvecs = None
        self.tvecs = None
        self.calibration_error = None

        # 图像尺寸
        self.img_size = None

    def capture_calibration_images(self, hCamera, pFrameBuffer, num_images=20, save_dir="calibration_images"):
        """
        使用相机捕获标定图像（实时采集，需 mvsdk + 实体相机）

        Args:
            hCamera: 相机句柄
            pFrameBuffer: 帧缓冲区
            num_images: 需要捕获的图像数量
            save_dir: 保存图像的目录
        """
        import libs.vendor_libs.mvsdk as mvsdk
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        print(f"开始捕获标定图像，需要 {num_images} 张图像")
        print("按 's' 键保存图像，按 'q' 键退出")

        captured_count = 0

        while captured_count < num_images:
            try:
                # 从相机获取图像
                pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
                mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
                mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

                # 转换为 OpenCV 格式
                frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
                frame = np.frombuffer(frame_data, dtype=np.uint8)
                frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth,
                                       1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

                # 如果是彩色图像，转换为灰度图进行角点检测
                if len(frame.shape) == 3:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    display_frame = frame.copy()
                else:
                    gray = frame
                    display_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

                # 查找棋盘角点
                ret, corners = cv2.findChessboardCorners(gray, self.checkerboard_size, None)

                # 添加调试信息
                if not hasattr(self, '_debug_printed'):
                    print(f"调试信息: 寻找棋盘尺寸 {self.checkerboard_size} (列x行)")
                    print(f"图像尺寸: {gray.shape}")
                    self._debug_printed = True

                # 如果找到角点，在图像上绘制
                if ret:
                    # 提高角点精度
                    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                    corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

                    # 绘制角点
                    cv2.drawChessboardCorners(display_frame, self.checkerboard_size, corners2, ret)

                    # 显示状态信息
                    status_text = f"找到棋盘! 已捕获: {captured_count}/{num_images} 按's'保存"
                    cv2.putText(display_frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                                0.7, (0, 255, 0), 2)

                    # 添加更多提示信息
                    hint_text = f"检测到 {len(corners)} 个角点"
                    cv2.putText(display_frame, hint_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, (0, 255, 0), 1)
                else:
                    status_text = f"未找到棋盘 已捕获: {captured_count}/{num_images}"
                    cv2.putText(display_frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                                0.7, (0, 0, 255), 2)

                    # 添加提示信息
                    hint_text = f"请调整棋盘位置,需要 {self.checkerboard_size[0]}x{self.checkerboard_size[1]} 格"
                    cv2.putText(display_frame, hint_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, (0, 0, 255), 1)

                # 显示图像
                cv2.namedWindow("Camera Calibration", cv2.WINDOW_NORMAL)
                cv2.imshow("Camera Calibration", display_frame)

                # 检测按键
                key = cv2.waitKey(1) & 0xFF
                if key == ord('s'):  # 按 's' 键保存图像
                    if ret:  # 只有找到棋盘时才能保存
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = os.path.join(save_dir, f"calibration_{timestamp}_{captured_count:02d}.jpg")
                        success = cv2.imwrite(filename, frame)
                        if success:
                            print(f"保存图像: {filename}")
                            captured_count += 1
                        else:
                            print(f"保存图像失败: {filename}")
                    else:
                        print("未检测到棋盘，无法保存图像！请确保棋盘完整可见")
                elif key == ord('q'):  # 退出
                    print("用户退出捕获")
                    break
                elif key != 255:  # 检测到其他按键
                    print(f"按键检测: {chr(key) if 32 <= key <= 126 else key} (按's'保存, 按'q'退出)")

            except mvsdk.CameraException as e:
                if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
                    print(f"CameraGetImageBuffer failed({e.error_code}): {e.message}")

        cv2.destroyAllWindows()
        print(f"图像捕获完成，共保存 {captured_count} 张图像")
        return captured_count

    def load_images_from_directory(self, image_dir="calibration_images"):
        """
        从目录加载标定图像并检测角点（不依赖相机 SDK）

        Args:
            image_dir: 图像目录路径
        """
        # 支持的图像格式
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
        image_paths = []

        for ext in image_extensions:
            image_paths.extend(glob.glob(os.path.join(image_dir, ext)))
            image_paths.extend(glob.glob(os.path.join(image_dir, ext.upper())))

        if not image_paths:
            print(f"在目录 {image_dir} 中未找到图像文件")
            return False

        print(f"找到 {len(image_paths)} 张图像，开始处理...")

        valid_images = 0

        for img_path in image_paths:
            # 读取图像
            img = cv2.imread(img_path)
            if img is None:
                print(f"无法读取图像: {img_path}")
                continue

            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 设置图像尺寸（第一张图像）
            if self.img_size is None:
                self.img_size = gray.shape[::-1]

            # 查找棋盘角点
            ret, corners = cv2.findChessboardCorners(gray, self.checkerboard_size, None)

            if ret:
                # 提高角点精度
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

                # 保存点对
                self.objpoints.append(self.objp)
                self.imgpoints.append(corners2)
                valid_images += 1
                print(f"处理成功: {os.path.basename(img_path)}")
            else:
                print(f"未找到角点: {os.path.basename(img_path)}")

        print(f"成功处理 {valid_images} 张图像")
        return valid_images > 0

    def calibrate_camera(self):
        """
        执行相机标定
        """
        if len(self.objpoints) == 0 or len(self.imgpoints) == 0:
            print("错误: 没有有效的标定点")
            return False

        if self.img_size is None:
            print("错误: 图像尺寸未设置")
            return False

        print(f"开始相机标定，使用 {len(self.objpoints)} 张图像...")

        # 执行标定
        ret, self.camera_matrix, self.dist_coeffs, self.rvecs, self.tvecs = cv2.calibrateCamera(
            self.objpoints, self.imgpoints, self.img_size, None, None)

        if ret:
            self.calibration_error = ret
            print("相机标定成功!")
            print(f"重投影误差: {ret:.4f}")
            print(f"相机内参矩阵:\n{self.camera_matrix}")
            print(f"畸变系数: {self.dist_coeffs.ravel()}")
            return True
        else:
            print("相机标定失败!")
            return False

    def save_calibration(self, filename="camera_calibration.pkl"):
        """
        保存标定结果到文件

        Args:
            filename: 保存文件名
        """
        if self.camera_matrix is None:
            print("错误: 没有标定结果可保存")
            return False

        calibration_data = {
            'camera_matrix': self.camera_matrix,
            'dist_coeffs': self.dist_coeffs,
            'rvecs': self.rvecs,
            'tvecs': self.tvecs,
            'calibration_error': self.calibration_error,
            'img_size': self.img_size,
            'checkerboard_size': self.checkerboard_size,
            'square_size': self.square_size
        }

        if save_calibration_data(calibration_data, filename):
            print(f"标定结果已保存到: {filename}")
            return True
        return False

    def load_calibration(self, filename="camera_calibration.pkl"):
        """
        从文件加载标定结果

        Args:
            filename: 标定文件名
        """
        try:
            calibration_data = load_calibration_data(filename)

            self.camera_matrix = calibration_data['camera_matrix']
            self.dist_coeffs = calibration_data['dist_coeffs']
            self.rvecs = calibration_data.get('rvecs')
            self.tvecs = calibration_data.get('tvecs')
            self.calibration_error = calibration_data.get('calibration_error')
            self.img_size = calibration_data['img_size']
            self.checkerboard_size = calibration_data.get('checkerboard_size', self.checkerboard_size)
            self.square_size = calibration_data.get('square_size', self.square_size)

            print(f"标定结果已从 {filename} 加载")
            if self.calibration_error is not None:
                print(f"重投影误差: {self.calibration_error:.4f}")
            return True
        except Exception as e:
            print(f"加载失败: {e}")
            return False

    def undistort_image(self, img):
        """
        对图像进行畸变校正

        Args:
            img: 输入图像

        Returns:
            校正后的图像
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            print("错误: 没有标定数据")
            return img

        h, w = img.shape[:2]
        print(f"输入图像尺寸: {w}x{h}")

        # 获取优化的新相机矩阵
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), 1, (w, h))

        print(f"ROI区域: x={roi[0]}, y={roi[1]}, w={roi[2]}, h={roi[3]}")

        # 畸变校正
        dst = cv2.undistort(img, self.camera_matrix, self.dist_coeffs, None, newcameramtx)

        # 安全地裁剪图像到有效区域
        x, y, w_roi, h_roi = roi
        if w_roi > 0 and h_roi > 0 and x >= 0 and y >= 0:
            # 确保裁剪区域在图像范围内
            x = max(0, x)
            y = max(0, y)
            x_end = min(dst.shape[1], x + w_roi)
            y_end = min(dst.shape[0], y + h_roi)

            if x_end > x and y_end > y:
                dst = dst[y:y_end, x:x_end]
                print(f"裁剪后图像尺寸: {dst.shape[1]}x{dst.shape[0]}")
            else:
                print("警告: ROI区域无效，返回完整校正图像")
                print(f"完整校正图像尺寸: {dst.shape[1]}x{dst.shape[0]}")
        else:
            print("警告: ROI区域无效，返回完整校正图像")
            print(f"完整校正图像尺寸: {dst.shape[1]}x{dst.shape[0]}")

        return dst

    def test_undistortion(self, test_image_path=None, image_dir="calibration_images"):
        """
        测试畸变校正效果

        Args:
            test_image_path: 测试图像路径
            image_dir: 如果没有指定测试图像，从此目录选择
        """
        if self.camera_matrix is None:
            print("错误: 没有标定数据")
            return

        if test_image_path is None:
            # 从标定图像目录选择一张图像
            image_paths = glob.glob(os.path.join(image_dir, "*.jpg"))
            if not image_paths:
                print("没有找到测试图像")
                return
            test_image_path = image_paths[0]

        # 读取测试图像
        img = cv2.imread(test_image_path)
        if img is None:
            print(f"无法读取图像: {test_image_path}")
            return

        print(f"原始图像尺寸: {img.shape}")

        # 畸变校正
        undistorted = self.undistort_image(img)
        print(f"校正后图像尺寸: {undistorted.shape}")

        # 安全的图像对比显示
        try:
            # 检查图像尺寸是否相同
            if img.shape != undistorted.shape:
                print("图像尺寸不同，调整后显示对比")
                # 将校正后的图像调整到原图尺寸
                h_orig, w_orig = img.shape[:2]
                undistorted_resized = cv2.resize(undistorted, (w_orig, h_orig))

                # 添加标签
                img_labeled = img.copy()
                undistorted_labeled = undistorted_resized.copy()
                cv2.putText(img_labeled, "Original", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(undistorted_labeled, "Undistorted", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                # 水平拼接
                comparison = np.hstack((img_labeled, undistorted_labeled))
            else:
                print("图像尺寸相同，直接显示对比")
                # 添加标签
                img_labeled = img.copy()
                undistorted_labeled = undistorted.copy()
                cv2.putText(img_labeled, "Original", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(undistorted_labeled, "Undistorted", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                # 水平拼接
                comparison = np.hstack((img_labeled, undistorted_labeled))

            # 显示结果
            cv2.namedWindow("Original vs Undistorted", cv2.WINDOW_NORMAL)
            cv2.imshow("Original vs Undistorted", comparison)
            print("按任意键关闭窗口...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        except Exception as e:
            print(f"图像拼接失败: {e}")
            print("分别显示两张图像")

            # 分别显示
            cv2.namedWindow("Original Image", cv2.WINDOW_NORMAL)
            cv2.namedWindow("Undistorted Image", cv2.WINDOW_NORMAL)
            cv2.imshow("Original Image", img)
            cv2.imshow("Undistorted Image", undistorted)
            print("按任意键关闭窗口...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    def test_checkerboard_detection(self, test_image_path=None):
        """
        测试棋盘检测功能，帮助调试棋盘格式

        Args:
            test_image_path: 测试图像路径
        """
        if test_image_path is None:
            print("请提供测试图像路径")
            return

        # 读取测试图像
        img = cv2.imread(test_image_path)
        if img is None:
            print(f"无法读取图像: {test_image_path}")
            return

        # 转换为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        print(f"图像尺寸: {gray.shape}")
        print(f"寻找棋盘尺寸: {self.checkerboard_size} (内角点)")
        print(f"对应格子数量: {self.checkerboard_size[0]+1}x{self.checkerboard_size[1]+1}")

        # 尝试不同的标志位
        flags_to_try = [
            (cv2.CALIB_CB_ADAPTIVE_THRESH, "ADAPTIVE_THRESH"),
            (cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE, "ADAPTIVE_THRESH + NORMALIZE"),
            (cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FILTER_QUADS, "ADAPTIVE_THRESH + FILTER_QUADS"),
            (None, "默认")
        ]

        for flags, desc in flags_to_try:
            print(f"\n尝试检测方法: {desc}")

            if flags is None:
                ret, corners = cv2.findChessboardCorners(gray, self.checkerboard_size, None)
            else:
                ret, corners = cv2.findChessboardCorners(gray, self.checkerboard_size, flags)

            if ret:
                print(f"成功检测到 {len(corners)} 个角点")

                # 绘制检测结果
                display_img = img.copy()
                cv2.drawChessboardCorners(display_img, self.checkerboard_size, corners, ret)

                # 添加信息文本
                cv2.putText(display_img, f"Method: {desc}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_img, f"Found {len(corners)} corners", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # 显示结果
                cv2.namedWindow(f"Detection Result - {desc}", cv2.WINDOW_NORMAL)
                cv2.imshow(f"Detection Result - {desc}", display_img)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

                return True
            else:
                print(f"未检测到角点")

        print(f"\n所有方法都无法检测到棋盘，请检查:")
        print(f"1. 棋盘是否有 {self.checkerboard_size[0]+1}x{self.checkerboard_size[1]+1} 个格子")
        print(f"2. 格子是否完美的正方形")
        print(f"3. 黑白格子是否严格交替")
        print(f"4. 棋盘是否完全在图像内")
        print(f"5. 图像是否清晰，没有模糊")

        return False


def initialize_camera():
    """
    独立的相机初始化功能（实时采集，需 mvsdk + 实体相机）

    Returns:
        tuple: (hCamera, pFrameBuffer) 成功时返回相机句柄和帧缓冲区，失败时返回 (None, None)
    """
    try:
        import libs.vendor_libs.mvsdk as mvsdk
    except ImportError as e:
        print(f"无法导入相机 SDK (mvsdk): {e}")
        return None, None
    try:
        # 初始化SDK
        mvsdk.CameraSdkInit(1)
        print("SDK 初始化成功!")

        # 枚举相机
        DevList = mvsdk.CameraEnumerateDevice()
        nDev = len(DevList)

        if nDev < 1:
            print("未找到相机!")
            return None, None

        # 显示可用相机
        for i, DevInfo in enumerate(DevList):
            print("{}: {} {}".format(i, DevInfo.GetFriendlyName(), DevInfo.GetPortType()))

        # 选择相机
        camera_index = 0 if nDev == 1 else int(input("选择相机序号: "))
        DevInfo = DevList[camera_index]
        print(f"选择的相机: {DevInfo.GetFriendlyName()}")

        # 打开相机
        hCamera = mvsdk.CameraInit(DevInfo, -1, -1)

        # 获取相机特性描述
        cap = mvsdk.CameraGetCapability(hCamera)

        # 判断是黑白相机还是彩色相机
        monoCamera = (cap.sIspCapacity.bMonoSensor != 0)

        # 设置输出格式
        if monoCamera:
            mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
        else:
            mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

        # 相机模式切换成连续采集
        mvsdk.CameraSetTriggerMode(hCamera, 0)

        # 手动曝光，曝光时间30ms
        mvsdk.CameraSetAeState(hCamera, 0)
        mvsdk.CameraSetExposureTime(hCamera, 30 * 1000)

        # 让SDK内部取图线程开始工作
        mvsdk.CameraPlay(hCamera)

        # 计算RGB buffer所需的大小
        FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if monoCamera else 3)

        # 分配RGB buffer，用来存放ISP输出的图像
        pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

        print("相机初始化完成!")
        return hCamera, pFrameBuffer

    except mvsdk.CameraException as e:
        print(f"相机初始化失败({e.error_code}): {e.message}")
        return None, None
    except Exception as e:
        print(f"初始化过程中发生错误: {e}")
        return None, None


def cleanup_camera(hCamera, pFrameBuffer):
    """
    清理相机资源

    Args:
        hCamera: 相机句柄
        pFrameBuffer: 帧缓冲区
    """
    try:
        import libs.vendor_libs.mvsdk as mvsdk
        if hCamera is not None:
            mvsdk.CameraUnInit(hCamera)
            print("相机已关闭")

        if pFrameBuffer is not None:
            mvsdk.CameraAlignFree(pFrameBuffer)
            print("缓冲区已释放")

    except Exception as e:
        print(f"清理资源时发生错误: {e}")


def main():
    """命令行入口：标定 / 实时采集标定 / 加载测试 / 棋盘检测。"""
    parser = argparse.ArgumentParser(description="相机标定工具")
    sub = parser.add_subparsers(dest="action", required=True)

    p_images = sub.add_parser("from-images", help="从现有图像目录标定")
    p_images.add_argument("--image-dir", default="calibration_images")

    p_capture = sub.add_parser("capture", help="实时捕获图像并标定（需相机 + mvsdk）")
    p_capture.add_argument("--num", type=int, default=20, help="捕获图像数量")

    p_load = sub.add_parser("load", help="加载已有标定结果并做畸变校正测试")
    p_load.add_argument("--file", default="camera_calibration.pkl")

    p_board = sub.add_parser("test-board", help="测试棋盘格角点检测")
    p_board.add_argument("image", help="测试图像路径")

    args = parser.parse_args()
    calibrator = CameraCalibrator(checkerboard_size=(10, 7), square_size=18.0)

    if args.action == "from-images":
        if calibrator.load_images_from_directory(args.image_dir):
            if calibrator.calibrate_camera():
                calibrator.save_calibration()
                calibrator.test_undistortion()

    elif args.action == "capture":
        try:
            hCamera, pFrameBuffer = initialize_camera()
            if hCamera is None:
                print("相机初始化失败")
                return
            captured = calibrator.capture_calibration_images(hCamera, pFrameBuffer, args.num)
            if captured > 10:  # 至少需要10张图像
                if calibrator.load_images_from_directory():
                    if calibrator.calibrate_camera():
                        calibrator.save_calibration()
                        calibrator.test_undistortion()
            cleanup_camera(hCamera, pFrameBuffer)
        except Exception as e:
            print(f"相机初始化失败: {e}")

    elif args.action == "load":
        if calibrator.load_calibration(args.file):
            calibrator.test_undistortion()

    elif args.action == "test-board":
        if os.path.exists(args.image):
            calibrator.test_checkerboard_detection(args.image)
        else:
            print("图像文件不存在")


if __name__ == "__main__":
    main()
