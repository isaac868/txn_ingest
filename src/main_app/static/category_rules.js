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
        rule.querySelector('input[type="text"]').value = '';
        rule.querySelector('select').value = 'contains';
    } else {
        var deleteInput = rule.querySelector('input[type="hidden"][name$="-DELETE"]');
        deleteInput.value = 'on';
        rule.style.display = 'none';
    }
}

function newRule(button) {
    var rulesWrapper = button.previousElementSibling;
    var lastRule = rulesWrapper.lastElementChild;
    var newRule = lastRule.cloneNode(true);
    newRule.style.display = 'flex';

    // Clear input values and update id and name attributes
    var lambda = function (element) {
        for (var i = 0; i < element.children.length; i++) {
            var child = element.children[i];
            if (child.tagName === 'INPUT') {
                child.value = '';
            }
            if (child.tagName === 'SELECT') {
                child.value = 'contains';
            }
            if (child.id !== '') {
                child.id = child.id.replace(/\d+(?!.*\d)/, function (match) {
                    return parseInt(match) + 1;
                });
            }
            if (child.hasAttribute('name')) {
                child.setAttribute('name', child.getAttribute('name').replace(/\d+(?!.*\d)/, function (match) {
                    return parseInt(match) + 1;
                }));
            }
            lambda(child);
        }
    }
    lambda(newRule);

    // Update TOTAL_FORMS
    var totalForms = document.querySelector(`#${rulesWrapper.parentElement.id} input[name$='-TOTAL_FORMS']`);
    totalForms.value = parseInt(totalForms.value) + 1;

    rulesWrapper.appendChild(newRule);
}

function onDeleteCategory(button) {
    var categoryDiv = button.parentElement.parentElement.parentElement.parentElement;
    var deleteInput = button.nextElementSibling;
    deleteInput.value = 'on';
    categoryDiv.style.display = 'none';
}

Sortable.create(sortableContainer, {filter: 'button, select, input', preventOnFilter: false});