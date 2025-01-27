function onclickChevron(button) {
    button.classList.toggle('rotated');
}

function onDeleteRule(button) {
    var rule = button.parentElement;
    var rulesWrapper = rule.parentElement;
    var visibleRules = 0;
    for (var i = 0; i < rulesWrapper.children.length; i++) {
        if (rulesWrapper.children[i].style.display !== 'none') {
            visibleRules++;
        }
    }
    if (visibleRules === 1) {
        var newRuleBtn = rulesWrapper.nextElementSibling;
        newRule(newRuleBtn);
    }
    var deleteInput = rule.querySelector('input[type="hidden"][name$="-DELETE"]');
    deleteInput.value = 'on';
    rule.style.display = 'none';
}

function newRule(button, forNewCategory = false) {
    var rulesWrapper = button.previousElementSibling;
    var lastRule = rulesWrapper.lastElementChild;
    var newRule = lastRule.cloneNode(true);
    newRule.removeAttribute('style');

    // Remove hidden id inputs, feedback text, and error styling
    elementsToDelete = newRule.querySelectorAll('.invalid-feedback, input[type="hidden"][name$="-id"]');
    for (var i = 0; i < elementsToDelete.length; i++) {
        elementsToDelete[i].remove();
    }
    newRule.querySelector('.form-control').classList.remove('is-invalid');

    // Clear input values and update id and name attributes
    var lambda = function (element) {
        for (var i = 0; i < element.children.length; i++) {
            var child = element.children[i];
            if (child.tagName === 'INPUT') {
                child.value = '';
            }
            if (child.tagName === 'SELECT') {
                options = child.querySelectorAll('option');
                for (var j = 0; j < options.length; j++) {
                    options[j].removeAttribute('selected');
                }
                child.querySelector('option[value="contains"]').setAttribute('selected', '');
            }
            if (child.id !== '') {
                child.id = child.id.replace(/\d+(?!.*\d)/, function (match) {
                    return (forNewCategory ? 0 : parseInt(match) + 1);
                });
            }
            if (child.hasAttribute('name')) {
                child.setAttribute('name', child.getAttribute('name').replace(/\d+(?!.*\d)/, function (match) {
                    return (forNewCategory ? 0 : parseInt(match) + 1);
                }));
            }
            lambda(child);
        }
    }
    lambda(newRule);

    // Update TOTAL_FORMS
    var totalForms = rulesWrapper.parentElement.querySelector('input[name$="-TOTAL_FORMS"]');
    totalForms.value = parseInt(totalForms.value) + 1;

    rulesWrapper.appendChild(newRule);
    if (!forNewCategory) {
        newRule.querySelector('input:not([type="hidden"])').focus();
    }
}

function onDeleteCategory(button) {
    var categoryDiv = button.parentElement.parentElement.parentElement.parentElement;
    var deleteInput = button.nextElementSibling;
    deleteInput.value = 'on';
    categoryDiv.style.display = 'none';
}

function newCategory() {
    var categoriesContainer = document.querySelector('#sortableContainer');
    var lastCategory = categoriesContainer.lastElementChild;
    var newCategory = lastCategory.cloneNode(true);
    newCategory.removeAttribute('style');

    // Remove hidden id inputs, feedback text, and error styling
    elementsToDelete = newCategory.querySelectorAll('.invalid-feedback, input[type="hidden"][name$="-id"]');
    for (var i = 0; i < elementsToDelete.length; i++) {
        elementsToDelete[i].remove();
    }
    newCategory.querySelector('.form-control').classList.remove('is-invalid');
    newCategory.querySelector('.card').classList.remove('border-danger');

    // Clear input values and update id and name attributes
    var lambda = function (element) {
        for (var i = 0; i < element.children.length; i++) {
            var child = element.children[i];
            if ((child.tagName === 'INPUT' || child.tagName === 'SELECT') && child.type !== 'hidden') {
                child.value = '';
            }
            if (child.hasAttribute('data-bs-target')) {
                child.setAttribute('data-bs-target', child.getAttribute('data-bs-target').replace(/\d+/, function (match) {
                    return parseInt(match) + 1;
                }));
            }
            if (child.hasAttribute('for')) {
                child.setAttribute('for', child.getAttribute('for').replace(/\d+/, function (match) {
                    return parseInt(match) + 1;
                }));
            }
            if (child.id !== '') {
                child.id = child.id.replace(/\d+/, function (match) {
                    return parseInt(match) + 1;
                });
            }
            if (child.hasAttribute('name')) {
                child.setAttribute('name', child.getAttribute('name').replace(/\d+/, function (match) {
                    return parseInt(match) + 1;
                }));
            }
            lambda(child);
        }
    }
    lambda(newCategory);

    // Create new blank rule form and delete the rest
    var rulesCollapsable = newCategory.querySelector('.collapse');
    var newRuleBtn = rulesCollapsable.querySelector('[id$="_new_rule_btn"]');
    newRule(newRuleBtn, true);
    var rulesWrapper = rulesCollapsable.querySelector('.rules-wrapper');
    var emptyRule = rulesWrapper.lastElementChild.cloneNode(true);
    rulesWrapper.textContent = '';
    rulesWrapper.appendChild(emptyRule);

    // Update ruleset management form to reflect single unfilled rule form
    var totalForms = rulesCollapsable.querySelector('input[name$="-TOTAL_FORMS"]');
    totalForms.value = 1;
    var initialForms = rulesCollapsable.querySelector('input[name$="-INITIAL_FORMS"]');
    initialForms.value = 0;

    // Update TOTAL_FORMS (first instance of TOTAL_FORMS input in document)
    var totalForms = document.querySelector('input[name$="-TOTAL_FORMS"]');
    totalForms.value = parseInt(totalForms.value) + 1;

    categoriesContainer.appendChild(newCategory);
    newCategory.querySelector('input:not([type="hidden"])').focus();
    rePrioritizeCategories();
    createSortable();
}

function rePrioritizeCategories() {
    var categories = document.querySelectorAll('.card');
    for (var i = 0; i < categories.length; i++) {
        categories[i].querySelector('input[name$="-priority"]').value = i;
    }
}

function createSortable() {
    Sortable.create(sortableContainer, { filter: 'button, select, input', preventOnFilter: false, onUpdate: rePrioritizeCategories });
}

// Enable bootstrap tooltips
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

rePrioritizeCategories();
createSortable();