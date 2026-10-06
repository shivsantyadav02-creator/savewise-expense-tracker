from flask import jsonify

def success_response(data=None, message="Operation completed successfully", status_code=200):
    """
    Constructs a uniform JSON success envelope:
    {
        "success": True,
        "data": <payload>,
        "message": <informative_string>
    }
    """
    return jsonify({
        "success": True,
        "data": data,
        "message": message
    }), status_code

def error_response(error_message: str, status_code: int = 400):
    """
    Constructs a uniform JSON error envelope:
    {
        "success": False,
        "error": <error_description>
    }
    """
    return jsonify({
        "success": False,
        "error": error_message
    }), status_code
