from web3 import Web3
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import Column,BigInteger, Float, String, DateTime, Integer, func
from datetime import datetime, timezone
import time 
import os
from dotenv import load_dotenv
from pathlib import Path

# получаем ключи через os.getenv
env_path = Path.cwd() / '.env' 
load_dotenv(env_path)

RPC_URL = os.getenv("RPC_URL")
DB_URL = os.getenv("DB_URL")

if not RPC_URL:
    raise ValueError("RPC_URL не найден в переменных окружения!")

PROXY_ADDRESS = "0x8ECC0B419dfe3AE197BC96f2a03636b5E1BE91db"

# Блок создания контракта = 17556156 (можно найти на Etherscan во вкладке Internal Txns)
DEPLOYMENT_BLOCK = 23356156 # получилось загрузить исторические данные только с этого блока  


ABI = [
    {"inputs": [], "name": "totalAssets", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}], "stateMutability": "view", "type": "function"}
]

Base = declarative_base()

class VaultMetric(Base):
    __tablename__ = 'vault_metrics'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    block_number = Column(BigInteger)
    tvl_assets = Column(Float)  # Сумма активов в токенах
    share_price = Column(Float) # Стоимость 1 доли
    raw_total_assets = Column(String) # Сохраняем сырое значение на всякий случай


class VaultETL:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.engine = create_engine(DB_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(PROXY_ADDRESS), 
            abi=ABI
        )

    def get_data_at_block(self, block_number):
        """Вспомогательная функция для извлечения данных на любом блоке"""
        raw_assets = self.contract.functions.totalAssets().call(block_identifier=block_number)
        raw_supply = self.contract.functions.totalSupply().call(block_identifier=block_number)
        decimals = self.contract.functions.decimals().call()
        
        block_info = self.w3.eth.get_block(block_number)
        dt = datetime.fromtimestamp(block_info['timestamp'], tz=timezone.utc)
        
        return VaultMetric(
            timestamp=dt,
            block_number=block_number,
            tvl_assets=raw_assets / (10**decimals),
            share_price=raw_assets / raw_supply if raw_supply > 0 else 1.0
        )

    def backfill_history(self, step=50000):
        """Собирает историю, если база пуста"""
        session = self.Session()
        # Проверяем, есть ли уже записи
        count = session.query(func.count(VaultMetric.id)).scalar()
        
        if count == 0:
            print("База пуста. Начинаю сбор исторической информации...")
            current_block = self.w3.eth.get_block('latest')['number']
            
            # Идем от блока деплоя до текущего с шагом
            for block in range(DEPLOYMENT_BLOCK, current_block, step):
                try:
                    metric = self.get_data_at_block(block)
                    time.sleep(0.1)
                    session.add(metric)
                    session.commit()
                    print(f"Исторические данные загружены: Блок {block}")
                except Exception as e:
                    session.rollback()
                    print(f"Ошибка на блоке {block}: {e}")
            print("Исторический сбор завершен.")
        else:
            print(f"В базе уже есть {count} записей. Пропускаю Backfill.")
        session.close()

    def run_live(self, interval=300):
        """Режим работы в реальном времени"""
        print("Запуск мониторинга в реальном времени...")
        while True:
            session = self.Session()
            try:
                latest_block = self.w3.eth.get_block('latest')['number']
                metric = self.get_data_at_block(latest_block)
                session.add(metric)
                session.commit()
                print(f"Новая метрика: {metric.timestamp} | TVL: {metric.tvl_assets:.2f}")
            except Exception as e:
                session.rollback()
                if "unique constraint" not in str(e).lower(): # Игнорируем если блок тот же
                    print(f"Ошибка Live-мониторинга: {e}")
            finally:
                session.close()
            time.sleep(interval)

if __name__ == "__main__":
    etl = VaultETL()
    # 1. Сначала проверяем историю (выполнится один раз за все время существования БД)
    #etl.backfill_history(step=10000) # Шаг ~1.5 дня (1 блок ~12 сек)
    etl.backfill_history(step=50000) # 
    # 2. Переходим к постоянному мониторингу
    etl.run_live(interval=300)
