from cmux.tasks.models import OutputFormat, SkillDef

definition = SkillDef(
    name="data_analysis",
    description="Analyze data, produce summary + charts",
    prompt_template=(
        "Analyze the following data/topic:\n\n{{task}}\n\n"
        "Deliverable:\n"
        "- Executive summary of findings\n"
        "- Key metrics and trends\n"
        "- Data visualizations (describe charts, generate if possible)\n"
        "- Statistical insights\n"
        "- Recommendations based on the data\n"
        "- Methodology notes\n\n"
        "Focus on insights that drive decisions."
    ),
    output_formats=[OutputFormat.MARKDOWN, OutputFormat.IMAGES],
    tools=["Read", "Write", "Bash"],
    template_files=[],
    time_estimate_manual_minutes=120,
    aliases=["analysis", "data", "analytics"],
    keywords=["data", "analysis", "analyze", "metrics", "charts", "trends", "statistics"],
)
