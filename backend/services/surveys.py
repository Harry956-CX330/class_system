"""Question/answer validation shared by schema and routes (legacy options supported)."""
import json
import threading
from fastapi import HTTPException

submission_lock = threading.Lock()

def options_list(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list) and all(isinstance(x,str) for x in parsed):
            return parsed
    except (ValueError,TypeError):
        pass
    return [x.strip() for x in value.replace("，", ",").split(",") if x.strip()]

def validate_questions(questions):
    for index, question in enumerate(questions,1):
        if not question.question_text.strip():
            raise ValueError(f"第 {index} 题题干不能为空")
        if question.question_type not in {"text","single","multiple","rating"}:
            raise ValueError("不支持的题型")
        if question.question_type in {"single","multiple"}:
            options = options_list(question.options)
            if not 2 <= len(options) <= 30 or any(not x.strip() or len(x)>300 for x in options) or len(set(options)) != len(options):
                raise ValueError(f"第 {index} 题需要 2 至 30 个不重复的有效选项")

def validate_answers(questions, answers):
    by_id = {q.id:q for q in questions}
    ids = [a.question_id for a in answers]
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise HTTPException(422,"请完整回答本问卷的每一道题，不能包含其他问卷或重复题目")
    result = []
    for answer in answers:
        q = by_id[answer.question_id]
        value = answer.answer_text.strip()
        if not value or len(value)>5000:
            raise HTTPException(422,"回答不能为空或超过 5000 字符")
        if q.question_type == "single" and value not in options_list(q.options):
            raise HTTPException(422,"单选题包含无效选项")
        if q.question_type == "multiple":
            chosen = options_list(value)
            if not chosen or len(set(chosen)) != len(chosen) or not set(chosen) <= set(options_list(q.options)):
                raise HTTPException(422,"多选题包含重复或无效选项")
            value = json.dumps(chosen, ensure_ascii=False)
        if q.question_type == "rating" and value not in {"1","2","3","4","5"}:
            raise HTTPException(422,"评分必须为 1 至 5 的整数")
        result.append((q.id,value))
    return result
