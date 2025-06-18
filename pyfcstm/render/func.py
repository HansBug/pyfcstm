import jinja2
from hbutils.reflection import quick_import_object


def process_item_to_object(f, env: jinja2.Environment):
    if isinstance(f, dict):
        type_ = f.pop('type', 'template')
        if type_ == 'template':
            params = f.pop('params', None)
            template = f.pop('template')
            if params is not None:  # with params order
                obj_template = env.from_string(template)

                def _fn_render(*args, **kwargs):
                    render_args = dict(zip(params, args))
                    return obj_template.render(**render_args, **kwargs)

                return _fn_render

            else:  # no params order
                return env.from_string(template).render

        elif type_ == 'import':
            from_ = f.pop('from')
            obj, _, _ = quick_import_object(from_)
            return obj

        elif type_ == 'value':
            value = f.pop('value')
            return value

        else:
            return f
    else:
        return f
