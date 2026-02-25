from typing import List
from schemas.audit_report import AuditSection, AuditIssue
from config.settings import settings
from utils.file_handler import FileHandler

class IntegrityProbe:
    def run(self, context: dict) -> AuditSection:
        """
        运行完整性检查
        :param context: 包含 'temp_dir' 等上下文信息
        :return: AuditSection
        """
        temp_dir = context.get("temp_dir")
        if not temp_dir:
            return AuditSection(
                name="Resource Integrity",
                status="FAIL",
                issues=[AuditIssue(severity="ERROR", code="SYS_ERR", message="Context missing temp_dir")]
            )

        missing_files = FileHandler.check_files_exist(temp_dir, settings.REQUIRED_RESOURCE_FILES)
        
        issues = []
        status = "PASS"
        
        if missing_files:
            status = "FAIL"
            for f in missing_files:
                issues.append(AuditIssue(
                    severity="ERROR", 
                    code="MISSING_FILE", 
                    message=f"Missing required resource file: {f}"
                ))
        
        return AuditSection(name="Resource Integrity", status=status, issues=issues)
