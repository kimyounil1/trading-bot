import argparse
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from scripts.agent_orchestrator import parse_args, check_stop_conditions, main

@pytest.fixture
def mock_report_root(tmp_path):
    with patch("scripts.agent_orchestrator.REPORT_ROOT", tmp_path):
        yield tmp_path

def test_parse_args_defaults():
    with patch("sys.argv", ["orchestrator.py"]):
        args = parse_args()
        assert args.max_iterations == 1
        assert args.scoped_review is True
        assert args.max_changed_files == 10
        assert args.continue_from_codex_todo is None

def test_parse_args_custom():
    with patch("sys.argv", [
        "orchestrator.py", 
        "--max-iterations", "5", 
        "--max-changed-files", "20",
        "--scoped-review"
    ]):
        args = parse_args()
        assert args.max_iterations == 5
        assert args.max_changed_files == 20
        assert args.scoped_review is True

def test_refuse_yolo_mode():
    with patch("sys.argv", ["orchestrator.py", "--gemini-approval-mode", "yolo"]):
        code = main()
        assert code == 2

def test_check_stop_conditions_max_files(tmp_path):
    changed_files = tmp_path / "changed_files.txt"
    changed_files.write_text("file1.py\nfile2.py\nfile3.py")
    
    reason = check_stop_conditions(tmp_path, max_changed_files=2, history=[])
    assert "Too many changed files" in reason

def test_check_stop_conditions_mixed_artifacts(tmp_path):
    changed_files = tmp_path / "changed_files.txt"
    changed_files.write_text("src/main.py\nmodels/model.joblib")
    
    reason = check_stop_conditions(tmp_path, max_changed_files=10, history=[])
    assert "Generated artifacts detected in diff" in reason

def test_check_stop_conditions_sensitive_files(tmp_path):
    changed_files = tmp_path / "changed_files.txt"
    changed_files.write_text("src/main.py\n.env")
    
    reason = check_stop_conditions(tmp_path, max_changed_files=10, history=[])
    assert "Sensitive files touched" in reason

def test_check_stop_conditions_repeated_failure(tmp_path):
    summary1 = tmp_path / "summary.json"
    summary1.write_text(json.dumps({
        "overall_status": "fail",
        "gemini_review_harness_exit_code": 1,
        "runtime_harness_exit_code": 0
    }))
    
    history = [{"output_dir": str(tmp_path)}]
    
    # Current run dir
    curr_dir = tmp_path / "curr"
    curr_dir.mkdir()
    summary2 = curr_dir / "summary.json"
    summary2.write_text(json.dumps({
        "overall_status": "fail",
        "gemini_review_harness_exit_code": 1,
        "runtime_harness_exit_code": 0
    }))
    
    reason = check_stop_conditions(curr_dir, max_changed_files=10, history=history)
    assert "Same failing check twice" in reason

@patch("scripts.agent_orchestrator.run_command")
def test_scoped_review_command_construction(mock_run, tmp_path, mock_report_root):
    with patch("sys.argv", [
        "orchestrator.py", 
        "--run-codex-review", 
        "--scoped-review",
        "--task", "test"
    ]):
        mock_run.return_value = 0
        main()
        
        # Check if codex was called with packet path instead of --uncommitted
        codex_call = [call for call in mock_run.call_args_list if call[0][0][0] == "codex"]
        assert len(codex_call) > 0
        args = codex_call[0][0][0]
        assert "review" in args
        assert any("review_packet.md" in arg for arg in args)
        assert "--uncommitted" not in args
        # Check that reasoning effort defaults to low
        assert "-c" in args
        assert any("model_reasoning_effort=\"low\"" in arg for arg in args)

@patch("scripts.agent_orchestrator.run_command")
def test_max_iterations_behavior(mock_run, tmp_path, mock_report_root):
    # Mocking Gemini, Post-Workflow, Codex to all succeed
    mock_run.return_value = 0
    
    # We need to make sure CODEX_REVIEW_AND_TODO.md is created so task_text is updated 
    # and loop continues (though loop continues anyway if run_codex_review is True)
    
    with patch("sys.argv", [
        "orchestrator.py", 
        "--run-gemini",
        "--run-codex-review",
        "--task", "initial task",
        "--max-iterations", "2"
    ]):
        # Mocking the file creation that would happen in run_command
        def side_effect(args, **kwargs):
            if "codex" in args:
                out_path = kwargs.get("stdout_copy_path")
                if out_path:
                    out_path.write_text("# NEXT_TODO for Gemini CLI\nNext task content")
            return 0
        
        mock_run.side_effect = side_effect
        
        main()
        
        # Iteration count check: Gemini called twice, Post twice, Codex twice
        gemini_calls = [c for c in mock_run.call_args_list if c[0][0][0] == "gemini"]
        assert len(gemini_calls) == 2
        
        # Verify second Gemini call has the TODO from Codex
        assert "Next task content" in gemini_calls[1][0][0][-1]
