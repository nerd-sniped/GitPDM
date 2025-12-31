# -*- coding: utf-8 -*-
"""
Tests for core.result module - Result and AppError types
"""

import pytest
from freecad_gitpdm.core.result import Result, AppError


class TestAppError:
    """Test AppError dataclass"""
    
    def test_create_basic_error(self):
        """Test creating a basic error"""
        error = AppError(code="TEST_ERROR", message="Test failed")
        assert error.code == "TEST_ERROR"
        assert error.message == "Test failed"
        assert error.details == ""
        assert error.meta is None
    
    def test_create_error_with_details(self):
        """Test creating error with details"""
        error = AppError(
            code="AUTH_ERROR",
            message="Authentication failed",
            details="Invalid token provided",
            meta={"status": 401}
        )
        assert error.code == "AUTH_ERROR"
        assert error.message == "Authentication failed"
        assert error.details == "Invalid token provided"
        assert error.meta == {"status": 401}
    
    def test_error_immutable(self):
        """Test that AppError is immutable (frozen dataclass)"""
        error = AppError(code="TEST", message="Test")
        with pytest.raises(AttributeError):
            error.code = "MODIFIED"


class TestResult:
    """Test Result type"""
    
    def test_success_result(self):
        """Test creating a success result"""
        result = Result.success("test_value")
        assert result.ok is True
        assert result.value == "test_value"
        assert result.error is None
    
    def test_failure_result(self):
        """Test creating a failure result"""
        result = Result.failure(
            code="FAILED",
            message="Operation failed",
            details="Detailed error info"
        )
        assert result.ok is False
        assert result.value is None
        assert result.error is not None
        assert result.error.code == "FAILED"
        assert result.error.message == "Operation failed"
        assert result.error.details == "Detailed error info"
    
    def test_unwrap_or_success(self):
        """Test unwrap_or on success result"""
        result = Result.success(42)
        assert result.unwrap_or(0) == 42
    
    def test_unwrap_or_failure(self):
        """Test unwrap_or on failure result"""
        result = Result.failure("ERROR", "Failed")
        assert result.unwrap_or(99) == 99
    
    def test_unwrap_or_none_value(self):
        """Test unwrap_or when value is None"""
        result = Result.success(None)
        assert result.unwrap_or("default") == "default"
    
    def test_result_immutable(self):
        """Test that Result is immutable"""
        result = Result.success("value")
        with pytest.raises(AttributeError):
            result.ok = False
    
    def test_typed_result(self):
        """Test Result with specific types"""
        # String result
        str_result: Result[str] = Result.success("hello")
        assert str_result.value == "hello"
        
        # Int result
        int_result: Result[int] = Result.success(123)
        assert int_result.value == 123
        
        # Dict result
        dict_result: Result[dict] = Result.success({"key": "value"})
        assert dict_result.value == {"key": "value"}
