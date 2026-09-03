import json
import subprocess
import unittest


class PayloadShapeTests(unittest.TestCase):
    def test_corpus_is_harmless_and_semantically_equivalent(self):
        proc=subprocess.run(['cloud-reference/bin/payload-shape-canary'],capture_output=True,text=True,check=True)
        data=json.loads(proc.stdout)
        self.assertEqual(data['semantic_result'],'cloudref-canary')
        self.assertGreaterEqual(len(data['cases']),3)
        banned=('token','password','credential','exploit','bypass','evade')
        for case in data['cases']:
            lower=case['command'].lower()
            self.assertFalse(any(word in lower for word in banned), case)
            result=subprocess.run(case['command'],shell=True,capture_output=True,text=True,check=True)
            self.assertEqual(result.stdout.strip(),'cloudref-canary')


if __name__ == '__main__':
    unittest.main()
