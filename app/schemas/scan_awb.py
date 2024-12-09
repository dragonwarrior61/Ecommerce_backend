from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Scan_awb(BaseModel):
    awb_number: Optional[str] = None
    awb_type: Optional[str] = None
    scan_date: Optional[datetime] = None
    user_id: Optional[int] = None

class Scan_awbCreate(Scan_awb):
    pass

class Scan_awbUpdate(Scan_awb):
    pass

class Scan_awbRead(Scan_awb):
    id: int

    class Config:
        orm_mode = True
