import unittest
from core.planner import PlanStep
from pydantic import ValidationError

class TestRFC003PlannerSchema(unittest.TestCase):
    
    def test_valid_read(self):
        """Test a valid read_file operation."""
        step = PlanStep(
            step_number=1,
            description="Read the project documentation.",
            action_type="read_file",
            target_path="README.md"
        )
        self.assertEqual(step.target_path, "README.md")

    def test_invalid_read_dash(self):
        """Test read_file with '-' target_path should fail."""
        with self.assertRaises(ValidationError) as ctx:
            PlanStep(
                step_number=1,
                description="Read README.md",
                action_type="read_file",
                target_path="-"
            )
        self.assertIn("executable target only inside the details field", str(ctx.exception))

    def test_invalid_read_empty(self):
        """Test read_file with empty target_path should fail."""
        with self.assertRaises(ValidationError) as ctx:
            PlanStep(
                step_number=1,
                description="Read README.md",
                action_type="read_file",
                target_path=""
            )
        self.assertIn("executable target only inside the details field", str(ctx.exception))

    def test_invalid_list(self):
        """Test list_dir with '-' target_path should fail."""
        with self.assertRaises(ValidationError) as ctx:
            PlanStep(
                step_number=1,
                description="Inspect context files.",
                action_type="list_dir",
                target_path="-"
            )
        self.assertIn("executable target only inside the details field", str(ctx.exception))
