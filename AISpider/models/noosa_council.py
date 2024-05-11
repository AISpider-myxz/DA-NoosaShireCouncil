from sqlalchemy import Column, String, Text, Integer, DateTime, func, UniqueConstraint
from .metadata_base import Base


class NoosaCouncil(Base):
    __tablename__ = 'noosa_council'
    id = Column(Integer, primary_key=True)
    application_id = Column(String(255), nullable=False, unique=True)
    application_type = Column(String(255), nullable=True,server_default=None)
    category = Column(String(255), nullable=True, server_default=None)
    lodgement_date = Column(Integer, nullable=True,)
    description = Column(Text, nullable=True)
    details = Column(Text, nullable=True, server_default=None)
    decision = Column(String(255), nullable=True, server_default=None)
    officer = Column(String(255), nullable=True, server_default=None)
    property_id = Column(String(255), nullable=True, default=None)
    address = Column(Text, nullable=True, server_default=None)
    land_description = Column(Text, nullable=True, server_default=None)
    names = Column(String(255), nullable=True, server_default=None)
    documents = Column(Text, nullable=True, server_default=None)

    _tid = Column(String(255), nullable=False,server_default=None)
    created_at = Column(DateTime, server_default=func.now())
    update_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

   