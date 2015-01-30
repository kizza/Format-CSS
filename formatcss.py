import sublime
import sublime_plugin
import pprint
import re



# ordering = [
# 		[
# 			'display',
# 			'clear'
# 			'position',
# 			'top',
# 			'left',
# 			'z-index'
# 		],
# 		['width'],
# 		['height']
# 	]

# def encode_attribute_for_ordering(a):
# 	index = 100
# 	for group in ordering:
# 		if a in group:
# 			a = str(index) + a
# 		index+= 1
# 	return a


# def decode_attribute_for_ordering(a):
# 	return re.sub('^\d+', '', a)
def sort_rule_attributes(selector, rules):
    sorted_rules = []
    # Keyed items
    attributes = []
    for rule in rules:
        if isinstance(rule, dict):
            attribute = rule['key']
            attributes.append(attribute)
    attributes.sort()
    # Append
    for a in attributes:
        for rule in rules:
            if isinstance(rule, dict):
                if (rule['key'] == a):
                    sorted_rules.append(rule)
                    rules.remove(rule)
    # other items
    for rule in rules:
        sorted_rules.append(rule)
    return sorted_rules


def rules_contain_comments(rules):
    for rule in rules:
        if isinstance(rule, dict):
            if rule['key'].startswith('/*'):
                return True
        else:
            if rule.startswith('/*'):
                return True
    return False


def replace_section(view, edit, region, selector, rules, runtype):
    # Setup
    inline_threshold = get_setting('inline_threshold', int)
    inline_wrap_length = get_setting('inline_wrap_length', int)
    tabs = '\t' * selector.count('\t')
    contains_comments = rules_contain_comments(rules)
    multiline = True if contains_comments else len(rules) >= inline_threshold
    # runtype override
    if runtype == 'strict':
        multiline = False
    # Format variables
    divider = "\n\t" + tabs if multiline else ''
    pad = '' if multiline else ' '
    # Sort attributes
    if not contains_comments:
        rules = sort_rule_attributes(selector, rules)
    # Compile output
    default_indent = len(selector.expandtabs(3))  # default indent as per the selector
    total_line_length = default_indent  # when inline, wrap at line length
    output = selector + ' {' + pad
    append_to_next_output = ''  # Hack appends ";" char sometimes
    for rule in rules:
        # Get next rule
        if isinstance(rule, dict):
            if multiline:
                next_rule = rule['key'] + ": " + rule['val'] + ";"
            else:
                next_rule = rule['key'] + ":" + rule['val'] + "; "
        else:
            next_rule = rule

        # This fixes the data image ';base64,'problem
        if next_rule.startswith('base64'):
            output += ';'
            append_to_next_output = ';'
        # This makes sure the base64 line ends with ";"
        elif append_to_next_output != '':
            output += append_to_next_output + divider
            append_to_next_output = ''
        else:
            output += divider

        # Wrap if inline and over line length
        if not multiline and not next_rule.startswith('base64'):
            if total_line_length + len(next_rule) > inline_wrap_length:
                # output+= str(total_line_length) +">"+ str(total_line_length + len(next_rule)) + " next="+ str(default_indent)
                output += "\n\t" + tabs
                total_line_length = default_indent + 3  # Return to default + an extra tab
        # Append next rule
        total_line_length += len(next_rule)
        output += next_rule
    output = output + "\n" + tabs if multiline else output.rstrip()
    output += pad + "}"
    # Update view
    view.replace(edit, region, output)


#
# Text Commands
#
class format_css_command(sublime_plugin.TextCommand):

    def run(self, edit, runtype='normal'):
        view = self.view

        # Only run with css files
        if 'css' not in view.settings().get('syntax').lower():
            return

        #  Remove double lines between css statements
        matches = view.find_all('\n\n+')
        for region in reversed(matches):
            view.replace(edit, sublime.Region(region.a, region.b), '\n\n')

        #  Replace 0px with 0
        matches = view.find_all('[0-9]+px')
        for region in reversed(matches):
            value = view.substr(region)
            if value == '0px':
                value = '0'
                view.replace(edit, sublime.Region(region.a, region.b), value)

        # Break into classname {attrbute:value}
        classname = '(\w|#|\.|:| |-|,|\*|\+|\"|\'|\=|\[|\]|>)+'
        matches = view.find_all('^( |\t)*?'+classname+'(\s+)?\{[^\}]*?\}')
        matches = reversed(matches)
        for region in (matches):
            # Get the text
            text = view.substr(region)
            text = text.rstrip()

            # Split into selector and rules
            bits = re.split(r'(\{|\})', text)
            selector = bits[0].rstrip()
            content = bits[2].strip()

            # Loop through to create rules stack
            rules = []
            # items = re.split(r'(;[^base]|\n)', content)	# added "base" so that it doesn't break on dataimage lines
            items = re.split(r'(;|\n)', content)
            for item in items:
                item = item.strip()
                if item != "" and item != ';':
                    pair = item.split(':')
                    if len(pair) == 2:
                        key = pair[0].strip()
                        val = pair[1].strip()
                        rules.append({'key': key, 'val': val})
                    else:
                        rules.append(item)

            # Replace selection with formatted rules
            replace_section(view, edit, region, selector, rules, runtype)


#
# Helpers
#


# Standard setting
def get_setting(name, typeof=str):
    settings = sublime.load_settings('formatcss.sublime-settings')
    setting = settings.get(name)
    if setting:
        if typeof == str:
            return setting
        if typeof == bool:
            return setting is True
        elif typeof == int:
            return int(settings.get(name, 500))
    else:
        if typeof == str:
            return ''
        else:
            return None


def var_dump(val):
    pprint.pprint(val)
