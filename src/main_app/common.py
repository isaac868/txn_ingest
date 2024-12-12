import re
from .models import Category

def evaluate_rule(rule, description_text):
    match rule.match_type:
        case "equals":
            return rule.match_text.lower() == description_text.lower()
        case "contains":
            return rule.match_text.lower() in description_text.lower()
        case "regex":
            return re.search(rule.match_text, description_text) is not None
        case "starts_with":
            return description_text.lower().startswith(rule.match_text.lower())
        case "ends_with":
            return description_text.lower().endswith(rule.match_text.lower())
        
def get_user_categorization_dicts(user_in):
    return {"dicts": [{"cat": cat, "rules": cat.rule_set.all()} for cat in Category.objects.filter(user=user_in)], "un_categorized": Category.get_uncategorized(user_in)}

def get_category(categorization_dicts, description_text):
    for dict in categorization_dicts["dicts"]:
        if any(evaluate_rule(rule, description_text) for rule in dict["rules"]):
            return dict["cat"]
    return categorization_dicts["un_categorized"]