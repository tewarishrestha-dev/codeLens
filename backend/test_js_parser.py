import tempfile
import unittest
from pathlib import Path
from app.services.js_parser import parse_js_file
from app.services.dependency_analyzer import build_dependencies


class TestJsParser(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_js_functions_and_classes(self):
        code = """
import React, { useState } from 'react';
import { helper } from './utils';
const config = require('./config');

export class AnalyticsTracker extends BaseTracker {
    constructor(props) {
        super(props);
    }

    trackEvent(eventName) {
        logMetric(eventName);
    }
}

export async function processData(items) {
    const valid = filterValid(items);
    return valid;
}

export const computeTotal = (price, tax) => {
    return calculate(price, tax);
};
"""
        file_path = self.tmp_path / "app.jsx"
        file_path.write_text(code, encoding="utf-8")

        result = parse_js_file(file_path)

        self.assertIn("react", result["imports"])
        self.assertIn("./utils", result["imports"])
        self.assertIn("./config", result["imports"])

        func_names = [f["name"] for f in result["functions"]]
        self.assertIn("processData", func_names)
        self.assertIn("computeTotal", func_names)

        self.assertEqual(len(result["classes"]), 1)
        cls = result["classes"][0]
        self.assertEqual(cls["name"], "AnalyticsTracker")
        self.assertIn("BaseTracker", cls["bases"])
        method_names = [m["name"] for m in cls["methods"]]
        self.assertIn("trackEvent", method_names)

        call_targets = [c["calls"] for c in result["calls"]]
        self.assertIn("logMetric", call_targets)
        self.assertIn("filterValid", call_targets)
        self.assertIn("calculate", call_targets)

    def test_js_relative_dependencies(self):
        analysis = {
            "src/App.jsx": {
                "imports": ["./components/Header", "./utils/api"],
                "functions": [{"name": "App", "line": 5, "arguments": []}],
                "classes": [],
                "calls": []
            },
            "src/components/Header.jsx": {
                "imports": ["../utils/api"],
                "functions": [{"name": "Header", "line": 2, "arguments": []}],
                "classes": [],
                "calls": []
            },
            "src/utils/api.js": {
                "imports": [],
                "functions": [{"name": "fetchData", "line": 1, "arguments": []}],
                "classes": [],
                "calls": []
            }
        }
        deps = build_dependencies(analysis)
        self.assertIn("src/components/Header.jsx", deps["forward"]["src/App.jsx"])
        self.assertIn("src/utils/api.js", deps["forward"]["src/App.jsx"])
        self.assertIn("src/utils/api.js", deps["forward"]["src/components/Header.jsx"])
        self.assertIn("src/App.jsx", deps["reverse"]["src/utils/api.js"])


if __name__ == "__main__":
    unittest.main()
