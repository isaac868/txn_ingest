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

def get_category(user_in, description_text):
    for category in Category.objects.filter(user=user_in):
        if any(evaluate_rule(rule, description_text) for rule in category.rule_set.all()):
            return category
    return Category.get_uncategorized(user_in)