import tempfile
import unittest
from pathlib import Path
from app import analyze, create_app, extract_skills

class CareerLensTests(unittest.TestCase):
    def test_matching(self):
        result = analyze("Python SQL Flask", "Seeking Python and SQL experience")
        self.assertEqual(result["coverage"], 100.0)
        self.assertEqual(result["missing"], [])
    def test_missing_skills(self):
        self.assertIn("docker", analyze("Python developer", "Python and Docker")["missing"])
    def test_boundaries(self):
        self.assertNotIn("sql", extract_skills("nosql"))
    def test_empty(self):
        with self.assertRaises(ValueError): analyze("", "job")
    def test_route(self):
        with tempfile.TemporaryDirectory() as folder:
            app = create_app({"TESTING": True, "DATABASE": str(Path(folder) / "test.db")})
            client = app.test_client()
            self.assertEqual(client.get("/").status_code, 200)
            response = client.post("/analyze", data={"role":"Data analyst", "resume":"Python SQL", "job":"Python SQL Excel"})
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Your compatibility report", response.data)
            self.assertEqual(client.post("/clear").status_code, 302)

if __name__ == "__main__": unittest.main()
