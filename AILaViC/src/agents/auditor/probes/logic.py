from typing import Dict, Any, List
from schemas.audit_report import AuditSection, AuditIssue
from schemas.agent_data import ScenarioData, AgentInstance

class LogicProbe:
    def run(self, data: ScenarioData) -> AuditSection:
        issues = []
        
        # Build map for fast lookup
        # Some agents might not have agentId, so skip them
        agent_map = {a.agentId: a for a in data.agentInstances if a.agentId}
        
        # Check Causal Chains
        for agent in data.agentInstances:
            self._check_perception_action(agent, issues)
            self._check_command_response(agent, agent_map, issues)
            self._check_state_continuity(agent, issues)
        
        self._check_trigger_effect(data.agentInstances, issues)

        # Determine status
        status = "PASS"
        for i in issues:
            if i.severity in ["CRITICAL", "ERROR"]:
                status = "FAIL"
                break
            
        return AuditSection(name="Causal Chain Analysis", status=status, issues=issues)

    def _check_perception_action(self, agent: AgentInstance, issues: List[AuditIssue]):
        # 1.2.1 Perception-Decision-Action Chain
        # Rule: Agents with mission dynamics must have sensors (fldmds) or target inputs (vardefs)
        
        # Check if missionable (using Pydantic model extra fields or explicit fields)
        # agent is a Pydantic model, so use getattr or .dict() access if needed, 
        # but here we assume attributes are populated if they exist in JSON and extra='allow'
        
        # Note: In Pydantic v1/v2 compat, explicit fields are attributes. Extra fields might need .__dict__ or .model_extra
        # However, if the parser put them in __dict__, getattr works.
        
        has_mission = False
        mission_dyn = getattr(agent, "missionableDynamics", [])
        if mission_dyn:
            has_mission = True
        
        # Also check 'missionable' boolean if it exists
        if getattr(agent, "missionable", False):
            has_mission = True

        if not has_mission:
            return

        has_sensors = len(agent.fldmds) > 0
        
        # Check vardefs for target inputs
        vardefs = getattr(agent, "vardefs", [])
        has_target_input = False
        if vardefs:
            for v in vardefs:
                # v is likely a dict if parsed from JSON list of dicts
                if isinstance(v, dict):
                    name = v.get("varName", "").lower()
                else:
                    # If it's an object
                    name = getattr(v, "varName", "").lower()
                    
                if "target" in name or "navigatable" in name or "track" in name:
                    has_target_input = True
                    break
        
        if not has_sensors and not has_target_input:
            issues.append(AuditIssue(
                severity="WARNING",
                code="CAUSAL_PDA_MISSING_INPUT",
                message="Agent has mission capabilities but no defined sensors (fldmds) or target inputs.",
                entity_id=agent.instanceName,
                agent_name=getattr(agent, "agentName", "N/A"),
                evidence=f"Missionable: {has_mission}, Sensors: {len(agent.fldmds)}"
            ))

    def _check_command_response(self, agent: AgentInstance, agent_map: Dict[str, AgentInstance], issues: List[AuditIssue]):
        # 1.2.2 Command-Response Loop
        # Rule: Check parent existence and feedback status
        
        parent_id = getattr(agent, "asmParentPath", None)
        
        if parent_id and parent_id not in agent_map:
             issues.append(AuditIssue(
                severity="ERROR",
                code="CAUSAL_CMD_ORPHAN",
                message=f"Agent refers to non-existent parent ID: {parent_id}",
                entity_id=agent.instanceName,
                agent_name=getattr(agent, "agentName", "N/A"),
                evidence=f"asmParentPath: {parent_id}"
            ))
            
        # Check for feedback variables if it's a subordinate (has parent)
        # Only strict check if it has a parent
        if parent_id:
            vardefs = getattr(agent, "vardefs", [])
            has_status = False
            for v in vardefs:
                if isinstance(v, dict):
                    name = v.get("varName", "").lower()
                else:
                    name = getattr(v, "varName", "").lower()
                    
                if "status" in name or "state" in name or "report" in name:
                    has_status = True
                    break
            
            if not has_status:
                 issues.append(AuditIssue(
                    severity="WARNING",
                    code="CAUSAL_CMD_NO_FEEDBACK",
                    message="Agent has a commander but no status/feedback variables defined.",
                    entity_id=agent.instanceName,
                    agent_name=getattr(agent, "agentName", "N/A"),
                    evidence="Missing *status/state* in vardefs"
                ))

    def _check_state_continuity(self, agent: AgentInstance, issues: List[AuditIssue]):
        # 1.2.3 State Transition Continuity
        # Rule: Check initial state validity
        vardefs = getattr(agent, "vardefs", [])
        for v in vardefs:
            if isinstance(v, dict):
                name = v.get("varName", "")
                default = v.get("varDefault", [])
            else:
                name = getattr(v, "varName", "")
                default = getattr(v, "varDefault", [])
                
            if "status" in name.lower():
                if not default or (len(default) == 1 and default[0] == ""):
                     issues.append(AuditIssue(
                        severity="WARNING",
                        code="CAUSAL_STATE_INVALID_INIT",
                        message=f"State variable '{name}' has empty or invalid default value.",
                        entity_id=agent.instanceName,
                        agent_name=getattr(agent, "agentName", "N/A"),
                        evidence=f"varDefault: {default}"
                    ))

    def _check_trigger_effect(self, agents: List[AgentInstance], issues: List[AuditIssue]):
        # 1.2.4 Trigger-Effect Consistency
        # Rule: If Jamming exists, someone must be suppressible
        has_jammer = False
        jammer_name = ""
        
        for agent in agents:
            # Check description or sensors for jamming intent
            desc = (getattr(agent, "agentDesc", "") or "").lower()
            if "jamming" in desc or "干扰" in desc or "suppress" in desc:
                has_jammer = True
                jammer_name = agent.instanceName
                break
            
            for fld in agent.fldmds:
                # fld is dict
                fname = fld.get("fldmdName", "").lower()
                if "jam" in fname or "干扰" in fname:
                    has_jammer = True
                    jammer_name = agent.instanceName
                    break
            if has_jammer:
                break
        
        if has_jammer:
            # Check if any agent has suppression status
            has_victim_logic = False
            for agent in agents:
                vardefs = getattr(agent, "vardefs", [])
                for v in vardefs:
                    if isinstance(v, dict):
                        name = v.get("varName", "").lower()
                    else:
                        name = getattr(v, "varName", "").lower()
                        
                    if "suppress" in name or "jam" in name or "noise" in name or "interfere" in name:
                        has_victim_logic = True
                        break
                if has_victim_logic:
                    break
            
            if not has_victim_logic:
                issues.append(AuditIssue(
                    severity="WARNING",
                    code="CAUSAL_TE_NO_EFFECT",
                    message=f"Jammer '{jammer_name}' exists, but no agents have suppression/jamming status variables.",
                    entity_id="Global",
                    evidence="Trigger exists (Jammer), Effect missing (Status vars)"
                ))
