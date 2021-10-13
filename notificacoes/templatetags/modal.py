from django import template

register = template.Library()


#
# class CurrentTimeNode(template.Node):
#     def __init__(self, format_string):
#         self.format_string = str(format_string)
#
#     def render(self, context):
#         now = datetime.datetime.now()
#         return now.strftime(self.format_string)

@register.inclusion_tag('notificacoes/modal/campo.html')
def campo_modal(nome, valor, col=4):
    return locals()