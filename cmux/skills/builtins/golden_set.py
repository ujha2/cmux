from cmux.tasks.models import OutputFormat, SkillDef

definition = SkillDef(
    name="golden_set",
    description="Generate golden set / evaluation data",
    prompt_template=(
        "Generate a golden set / evaluation dataset for:\n\n{{task}}\n\n"
        "Requirements:\n"
        "- Clear schema with field definitions\n"
        "- Diverse, representative examples\n"
        "- Edge cases and boundary conditions\n"
        "- Expected outputs / labels for each example\n"
        "- At least 20-50 examples (or as specified)\n"
        "- Documentation of methodology\n\n"
        "Output in both CSV and JSON formats."
    ),
    output_formats=[OutputFormat.CSV, OutputFormat.JSON],
    tools=["Read", "Write"],
    template_files=[],
    time_estimate_manual_minutes=120,
    aliases=["golden", "eval_data", "evaluation", "test_data"],
    keywords=["golden set", "evaluation", "test data", "benchmark", "dataset", "ground truth"],
)
