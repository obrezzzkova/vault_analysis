from web3 import Web3
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import Column,BigInteger, Float, String, DateTime, Integer
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
import time 


PROXY_ADDRESS = "0x8ECC0B419dfe3AE197BC96f2a03636b5E1BE91db"
RPC_URL = 'https://mainnet.infura.io/v3/9ef49d8176c044f2b70603f164fc3dec'

# Строка подключения к PostgreSQL: "postgresql://user:password@localhost:5432/dbname"
DB_URL = "postgresql+psycopg2://nastya:nastyapassword@localhost:5432/nastyadb"


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

    def extract_and_transform(self):
        # Extract
        latest_block = self.w3.eth.get_block('latest')
        raw_assets = self.contract.functions.totalAssets().call()
        raw_supply = self.contract.functions.totalSupply().call()
        decimals = self.contract.functions.decimals().call()

        # Transform
        tvl_normalized = raw_assets / (10 ** decimals)
        
        # Рассчитываем цену доли: сколько активов дает 1 целая доля
        # Формула: (totalAssets / totalSupply)
        if raw_supply > 0:
            share_price = raw_assets / raw_supply
        else:
            share_price = 1.0

        return VaultMetric(
            block_number=latest_block['number'],
            tvl_assets=tvl_normalized,
            share_price=share_price,
            raw_total_assets=str(raw_assets)
        )
    
    def load(self, metric_obj):
        session = self.Session()
        try:
            session.add(metric_obj)
            session.commit()
            print(f"[{metric_obj.timestamp}] Block: {metric_obj.block_number} | TVL: {metric_obj.tvl_assets:.2f} | Price: {metric_obj.share_price:.6f}")
        except Exception as e:
            session.rollback()
            print(f"Ошибка записи в Postgres: {e}")
        finally:
            session.close()

    def run(self, interval=300):
        print("Запуск ETL пайплайна (PostgreSQL)...")
        while True:
            metric = self.extract_and_transform()
            self.load(metric)
            time.sleep(interval)

if __name__ == "__main__":
    etl = VaultETL()
    # Сбор данных каждые 5 минут
    etl.run(interval=300)