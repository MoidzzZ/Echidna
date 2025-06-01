import logging


def setup_logger(time):
    # 创建一个全局日志记录器
    logger = logging.getLogger('GlobalLogger')
    logger.setLevel(logging.INFO)  # 设置最低日志级别为 INFO

    # 防止重复添加处理器
    if not logger.handlers:
        # 创建文件处理器

        file_handler = logging.FileHandler(f'../rpg_system/log/experiment_{time}.log', mode='w', encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # 定义日志格式
        formatter = logging.Formatter('%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)

        # 将处理器添加到日志记录器
        logger.addHandler(file_handler)

    return logger
