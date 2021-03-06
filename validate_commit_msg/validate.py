#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import re
import sys
from enum import Enum

# constant
LINE_LIMIT = 100
BODY_REQUIRED = False
# TODO: moved to config later, changed to zh-CN after fix encoding issue
LANG = 'en'

TYPE_LIST = [
    'feat',  # 新功能（feature）
    'fix',  # 修补bug
    'docs',  # 文档（documentation）
    'style',  # 格式（不影响代码运行的变动）
    'refactor',  # 重构（既不是新增功能，也不是修改bug的代码变动）
    'perf',  # 提升性能（performance）
    'test',  # 增加测试
    'chore',  # 构建过程或辅助工具的变动'
    'revert',  # 撤销以前的 commit
    'Revert'  # 有些版本的工具生成的revert message首字母大写
]

# Error Enum
ErrorEnum = Enum('ErrorEnum',
                 ['VALIDATED',
                  'MERGE',
                  'ARG_MISSING',
                  'FILE_MISSING',
                  'EMPTY_MESSAGE',
                  'EMPTY_HEADER',
                  'BAD_HEADER_FORMAT',
                  'WRONG_TYPE',
                  'BODY_MISSING',
                  'NO_BLANK_LINE_BEFORE_BODY',
                  'LINE_OVERLONG'],
                 module=__name__)

# error message
# TODO: moved to config or lang file later
ERROR_MESSAGES = {
    'en': {
        # Normal case
        ErrorEnum.VALIDATED: '{errorname}: commit message meet the rule.',
        ErrorEnum.MERGE: '{errorname}: merge commit detected，skip check.',
        # File error
        ErrorEnum.ARG_MISSING: 'Error {errorname}: commit message file argument missing.',
        ErrorEnum.FILE_MISSING: 'Error {errorname}: file {filepath} not exists.',
        # Empty content
        ErrorEnum.EMPTY_MESSAGE: 'Error {errorname}: commit message has no content except whitespaces.',
        ErrorEnum.EMPTY_HEADER: 'Error {errorname}: header (first line) has no content except whitespaces.',
        # Header error
        ErrorEnum.BAD_HEADER_FORMAT: 'Error {errorname}: header (first line) not following the rule:\n{header}\nif you can not find any error after check, maybe you use Chinese colon, or lack of whitespace after the colon.',
        ErrorEnum.WRONG_TYPE: 'Error {errorname}: {type} one of the keywords:\n%s' % (', '.join(TYPE_LIST)),
        # Body error
        ErrorEnum.BODY_MISSING: 'Error {errorname}: body has no content except whitespaces.',  # 仅 BODY_REQUIRED 为 True时生效
        ErrorEnum.NO_BLANK_LINE_BEFORE_BODY: 'Error {errorname}: no empty line between header and body.',
        # Common error
        ErrorEnum.LINE_OVERLONG: 'Error {errorname}: the length of line is {length}, exceed %d:\n{line}' % (LINE_LIMIT)
    },
    'zh-CN': {
        # Normal case
        ErrorEnum.VALIDATED: '{errorname}：commit message 符合规范。',
        ErrorEnum.MERGE: '{errorname}：检测到 merge commit，跳过规范检查。',
        # File error
        ErrorEnum.ARG_MISSING: '错误 {errorname}：缺少 commit message 文件参数。',
        ErrorEnum.FILE_MISSING: '错误 {errorname}：文件 {filepath} 不存在。',
        # Empty content
        ErrorEnum.EMPTY_MESSAGE: '错误 {errorname}：commit message 没有内容或只有空白字符。',
        ErrorEnum.EMPTY_HEADER: '错误 {errorname}：header （首行） 没有内容或只有空白字符。',
        # Header error
        ErrorEnum.BAD_HEADER_FORMAT: '错误 {errorname}：header （首行） 不符合规范：\n{header}\n如果检查没有发现错误，请确认是否使用了中文冒号，以及冒号后面漏了空格。',
        ErrorEnum.WRONG_TYPE: '错误 {errorname}：{type} 不是以下关键字之一：\n%s' % (', '.join(TYPE_LIST)),
        # Body error
        ErrorEnum.BODY_MISSING: '错误 {errorname}：body 没有内容或只有空白字符。',  # 仅 BODY_REQUIRED 为 True时生效
        ErrorEnum.NO_BLANK_LINE_BEFORE_BODY: '错误 {errorname}：header 和 body 之间没有空一行。',
        # Common error
        ErrorEnum.LINE_OVERLONG: '错误 {errorname}：单行内容长度为{length}，超过了%d个字符：\n{line}' % (LINE_LIMIT)
    }
}

NON_FORMAT_ERROR = (
    ErrorEnum.VALIDATED,
    ErrorEnum.MERGE,
    ErrorEnum.ARG_MISSING,
    ErrorEnum.FILE_MISSING
)

# TODO: moved to config or lang file later
RULE_MESSAGE = {
    'en': '''
Commit message rule as follow:
<type>(<scope>): <subject>
// empty line
<body>
// empty line
<footer>

(<scope>), <body> and <footer> are optional
<type>  must be one of %s
more specific instructions, please refer to https://github.com/JayceChant/commit-msg.py''' % (', '.join(TYPE_LIST)),

    'zh-CN': '''
Commit message 的格式要求如下：
<type>(<scope>): <subject>
// 空一行
<body>
// 空一行
<footer>

其中 (<scope>) <body> 和 <footer> 可选
<type> 必须是 %s 中的一个
更详细的格式要求说明，请参考 https://github.com/JayceChant/commit-msg.py''' % (', '.join(TYPE_LIST))
}

MERGE_PATTERN = r'^Merge '
# 弱匹配，只检查基本的格式，各个部分允许为空，留到match.group(x)部分检查，以提供更详细的报错信息
HEADER_PATTERN = r'^((fixup! |squash! )?(\w+)(?:\(([^\)\s]+)\))?: (.+))(?:\n|$)'


# 这三种header需要在原header上添加关键字，会使原本不超字数的header超出字数
# SPECIAL_HEADER_PATTERN = r'^(fixup! |squash! |revert:)'


def print_error_msg(state, **kwargs):
    kwargs['errorname'] = state.name
    print(ERROR_MESSAGES[LANG][state].format(**kwargs))
    if state not in NON_FORMAT_ERROR:
        print(RULE_MESSAGE[LANG])


def check_header(header):
    if not header.strip():
        print_error_msg(ErrorEnum.EMPTY_HEADER)
        return False

    match = re.match(HEADER_PATTERN, header)
    if not match:
        # `.` not match newline in python, so `or not match.group(5).strip()` not necessary
        print_error_msg(ErrorEnum.BAD_HEADER_FORMAT, header=header)
        return False

    fixup_or_squash = bool(match.group(2))
    type_ = match.group(3)
    # scope = match.group(4) # TODO: 根据配置对scope检查
    # subject = match.group(5) # TODO: 根据规则对subject检查

    if type_ not in TYPE_LIST:
        print_error_msg(ErrorEnum.WRONG_TYPE, type=type_)

    # print(match.group(0, 1, 2, 3, 4, 5))

    length = len(header)
    if length > LINE_LIMIT and not (fixup_or_squash or type_ == 'revert' or type_ == 'Revert'):
        print_error_msg(ErrorEnum.LINE_OVERLONG, length=length, line=header)
        return False

    return True


def check_body(body):
    # body missing
    if not body.strip():
        if BODY_REQUIRED:
            print_error_msg(ErrorEnum.BODY_MISSING)
            return False
        else:
            return True

    if body.split('\n', maxsplit=1)[0]:
        print_error_msg(ErrorEnum.NO_BLANK_LINE_BEFORE_BODY)
        return False

    for line in body.splitlines():
        length = len(line)
        if length > LINE_LIMIT:
            print_error_msg(ErrorEnum.LINE_OVERLONG, length=length, line=line)
            return False

    return True


def validate_commit_message(message):
    """
    Validate the git commit message.
    :param message: the commit message to be validated.
    :return: True if the message meet the rule, False otherwise.
    """
    if not message.strip():
        print_error_msg(ErrorEnum.EMPTY_MESSAGE)
        return False

    if re.match(MERGE_PATTERN, message):
        print_error_msg(ErrorEnum.MERGE)
        return True

    header, body = message.split('\n', maxsplit=1)

    if not check_header(header):
        return False

    if not check_body(body):
        return False

    print_error_msg(ErrorEnum.VALIDATED)
    return True


def main():
    """
    Main function
    """
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not file_path:
        print_error_msg(ErrorEnum.ARG_MISSING)
        sys.exit(1)

    if not os.path.exists(file_path):
        print_error_msg(ErrorEnum.FILE_MISSING, filepath=file_path)
        sys.exit(1)

    with open(file_path, 'r', encoding='utf-8') as message_file:
        commit_msg = message_file.read()

    if not validate_commit_message(commit_msg):
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
