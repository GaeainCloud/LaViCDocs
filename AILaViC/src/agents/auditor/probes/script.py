from schemas.audit_report import AuditSection, AuditIssue
from schemas.agent_data import ScenarioData

class ScriptProbe:
    """
    审计 GaeaScript (ChaiScript) 脚本的引用和基本语法检查
    """
    def run(self, data: ScenarioData) -> AuditSection:
        issues = []
        status = "PASS"
        
        # 1. 遍历所有实体的 Doctrines
        for entity in data.agentInstances:
            if hasattr(entity, "doctrines") and entity.doctrines:
                for doctrine in entity.doctrines:
                    # 检查 Doctrine 结构
                    if not hasattr(doctrine, "doctActions"):
                         continue
                         
                    for action in doctrine.doctActions:
                        if hasattr(action, "handlingAgentActions"):
                            for handle_action in action.handlingAgentActions:
                                # 检查脚本关键字引用
                                keyword = getattr(handle_action, "keyword", None)
                                if not keyword:
                                    status = "FAIL"
                                    issues.append(AuditIssue(
                                        severity="WARNING",
                                        code="SCRIPT_NO_KEYWORD",
                                        message=f"Entity {entity.instanceName}: Doctrine action missing keyword",
                                        location=f"Entity:{entity.agentInstId}/Doctrine"
                                    ))
                                else:
                                    # TODO: 在这里可以根据 keyword 校验脚本是否存在 (如果脚本库已加载)
                                    pass
                                    
                                # 检查输入变量格式 (通常是 JSON 字符串)
                                input_var = getattr(handle_action, "inputVar", None)
                                if input_var:
                                    if not self._is_valid_json_string(input_var):
                                        status = "FAIL"
                                        issues.append(AuditIssue(
                                            severity="ERROR",
                                            code="SCRIPT_INVALID_INPUT",
                                            message=f"Entity {entity.instanceName}: Invalid JSON in inputVar for script {keyword}",
                                            location=f"Entity:{entity.agentInstId}/Script:{keyword}"
                                        ))

        return AuditSection(name="Script Validity", status=status, issues=issues)

    def _is_valid_json_string(self, s: str) -> bool:
        import json
        try:
            # inputVar 经常是 "{\"key\": val}" 格式
            # 有时可能包含 script 变量引用如 $$TargetId，这会导致 json 解析失败
            # GaeaScript 允许 $$ 变量，所以纯 JSON 校验可能太严格
            # 这里做一个宽松检查：如果是 { 开头，尝试解析，如果失败检查是否包含 $$
            s = s.strip()
            if not s.startswith("{"):
                return True # 可能不是 JSON
                
            json.loads(s)
            return True
        except:
            if "$$" in s:
                return True # 包含模板变量，视为有效
            return False
