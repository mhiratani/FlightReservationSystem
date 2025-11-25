from sqlalchemy import Column, Integer, String, Date, Time, Text, TIMESTAMP, Numeric
from sqlalchemy.sql import func
from app.database import Base

class Flight(Base):
    __tablename__ = "flights"
    
    id = Column(Integer, primary_key=True, index=True)
    flight_date = Column(Date, nullable=False)
    departure_airport = Column(String(3), nullable=False)
    arrival_airport = Column(String(3), nullable=False)
    reservation_number = Column(String(50), nullable=False)
    flight_number = Column(String(20), nullable=False)
    eticket_pdf_path = Column(String(255), nullable=True)
    seat_number = Column(String(10), nullable=True)
    status = Column(String(20), nullable=False, default="Reserved")
    departure_time = Column(Time, nullable=True)
    arrival_time = Column(Time, nullable=True)
    notes = Column(Text, nullable=True)
    payment_amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), nullable=True, default="JPY")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
