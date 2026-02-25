from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class AuditIssue(BaseModel):
    severity: str = Field(..., description="严重程度: ERROR, WARNING, INFO")
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误描述")
    location: Optional[str] = Field(None, description="问题发生的位置/字段")
    entity_id: Optional[str] = None
    agent_name: Optional[str] = None
    time_step: Optional[str] = None
    evidence: Optional[str] = None

class AuditSection(BaseModel):
    name: str
    status: str = Field(..., description="PASS, FAIL, WARN")
    issues: List[AuditIssue] = []

class AuditReport(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    overall_status: str = Field(..., description="PASS, FAIL")
    summary: str
    sections: Dict[str, AuditSection] = {}
    
    def add_section(self, name: str, status: str, issues: List[AuditIssue] = None):
        self.sections[name] = AuditSection(name=name, status=status, issues=issues or [])
