# Test Policy

## Required
- Unit tests for changed logic where practical.
- API tests for Dashboard endpoints.
- Script syntax checks for shell and Python.
- JSON validation for state and project files.

## CI Conditions
- Merge only when CI is green.
- Auto merge remains disabled unless explicitly enabled.
- CI repair stops when retry limits are reached.

## Coverage
- Target minimum coverage is 60% for application logic.
- For shell/control scripts, use focused smoke tests when unit coverage is impractical.

## Local Verification
```bash
python3 -m json.tool claudecode-devos/config/state.json >/dev/null
DEVOS_HOME="$PWD/claudecode-devos" python3 claudecode-devos/ops/validate_config.py
find claudecode-devos -type f -name '*.sh' -print0 | xargs -0 -I{} bash -n {}
python3 -m py_compile $(find claudecode-devos -type f -name '*.py' | sort)
shellcheck $(find claudecode-devos -type f -name '*.sh' | sort)
```
