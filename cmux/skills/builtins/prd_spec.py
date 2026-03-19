from cmux.tasks.models import OutputFormat, SkillDef

definition = SkillDef(
    name="prd_spec",
    description="PRD / spec writing with structured sections",
    prompt_template=(
        "Write a detailed Product Requirements Document (PRD) for:\n\n{{task}}\n\n"
        "Include these sections:\n"
        "1. Problem Statement\n"
        "2. Goals & Success Metrics\n"
        "3. User Stories\n"
        "4. Functional Requirements\n"
        "5. Non-Functional Requirements\n"
        "6. Design Considerations\n"
        "7. Dependencies & Risks\n"
        "8. Timeline & Milestones\n"
        "9. Open Questions\n\n"
        "Be specific, actionable, and include acceptance criteria where possible."
    ),
    output_formats=[OutputFormat.DOCX, OutputFormat.MARKDOWN],
    tools=["Read", "Write", "WebSearch"],
    template_files=["prd_structure.md"],
    time_estimate_manual_minutes=180,
    aliases=["prd", "spec", "requirements"],
    keywords=["prd", "spec", "requirements", "product requirements", "specification"],
)
