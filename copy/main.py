import asyncio
import logging
from telegram_client import TelegramSignalBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """主函数"""
    logger.info("="*50)
    logger.info("Telegram 群组信号跟单程序")
    logger.info("="*50)
    
    bot = TelegramSignalBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("\n正在停止程序...")
        bot.stop()
    except Exception as e:
        logger.error(f"程序出错: {e}")
        bot.stop()

if __name__ == "__main__":
    asyncio.run(main())

