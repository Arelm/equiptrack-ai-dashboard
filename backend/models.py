from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    TECHNICIAN = "TECHNICIAN"

class AssetStatusEnum(str, enum.Enum):
    OPERATIONAL = "OPERATIONAL"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    DECOMMISSIONED = "DECOMMISSIONED"
    FAULTY = "FAULTY"

class WorkOrderStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class PriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertTypeEnum(str, enum.Enum):
    MAINTENANCE_DUE = "MAINTENANCE_DUE"
    PART_LOW = "PART_LOW"
    ASSET_FAULT = "ASSET_FAULT"
    WARRANTY_EXPIRY = "WARRANTY_EXPIRY"
    WORK_ORDER_OVERDUE = "WORK_ORDER_OVERDUE"

class SeverityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Organization(Base):
    __tablename__ = "Organization"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    industry = Column(String)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, onupdate=func.now())

class User(Base):
    __tablename__ = "User"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(SAEnum(RoleEnum), default=RoleEnum.TECHNICIAN)
    organizationId = Column(String, ForeignKey("Organization.id"))
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, onupdate=func.now())

class Location(Base):
    __tablename__ = "Location"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String)
    organizationId = Column(String, ForeignKey("Organization.id"))
    createdAt = Column(DateTime, server_default=func.now())

class Asset(Base):
    __tablename__ = "Asset"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    serialNumber = Column(String)
    category = Column(String, nullable=False)
    status = Column(SAEnum(AssetStatusEnum), default=AssetStatusEnum.OPERATIONAL)
    organizationId = Column(String, ForeignKey("Organization.id"))
    locationId = Column(String, ForeignKey("Location.id"))
    purchaseDate = Column(DateTime)
    warrantyExpiry = Column(DateTime)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, onupdate=func.now())

class WorkOrder(Base):
    __tablename__ = "WorkOrder"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    priority = Column(SAEnum(PriorityEnum), default=PriorityEnum.MEDIUM)
    status = Column(SAEnum(WorkOrderStatusEnum), default=WorkOrderStatusEnum.OPEN)
    organizationId = Column(String, ForeignKey("Organization.id"))
    assetId = Column(String, ForeignKey("Asset.id"))
    locationId = Column(String, ForeignKey("Location.id"))
    dueDate = Column(DateTime)
    completedAt = Column(DateTime)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, onupdate=func.now())

class WorkOrderAssignment(Base):
    __tablename__ = "WorkOrderAssignment"
    id = Column(String, primary_key=True)
    workOrderId = Column(String, ForeignKey("WorkOrder.id"))
    userId = Column(String, ForeignKey("User.id"))
    assignedAt = Column(DateTime, server_default=func.now())

class MaintenanceLog(Base):
    __tablename__ = "MaintenanceLog"
    id = Column(String, primary_key=True)
    workOrderId = Column(String, ForeignKey("WorkOrder.id"))
    assetId = Column(String, ForeignKey("Asset.id"))
    userId = Column(String, ForeignKey("User.id"))
    notes = Column(String)
    hoursSpent = Column(Float)
    createdAt = Column(DateTime, server_default=func.now())

class PartsInventory(Base):
    __tablename__ = "PartsInventory"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    partNumber = Column(String)
    quantity = Column(Integer, default=0)
    reorderLevel = Column(Integer, default=5)
    unitCost = Column(Float)
    organizationId = Column(String, ForeignKey("Organization.id"))
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, onupdate=func.now())

class PartsUsed(Base):
    __tablename__ = "PartsUsed"
    id = Column(String, primary_key=True)
    maintenanceLogId = Column(String, ForeignKey("MaintenanceLog.id"))
    partId = Column(String, ForeignKey("PartsInventory.id"))
    quantityUsed = Column(Integer, nullable=False)
    createdAt = Column(DateTime, server_default=func.now())

class Alert(Base):
    __tablename__ = "Alert"
    id = Column(String, primary_key=True)
    type = Column(SAEnum(AlertTypeEnum), nullable=False)
    message = Column(String, nullable=False)
    severity = Column(SAEnum(SeverityEnum), default=SeverityEnum.MEDIUM)
    isRead = Column(Boolean, default=False)
    organizationId = Column(String, ForeignKey("Organization.id"))
    assetId = Column(String, ForeignKey("Asset.id"))
    createdAt = Column(DateTime, server_default=func.now())