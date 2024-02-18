class NotFound(Exception):
    pass


def get_log_wrapper(logger):
    def wrap_not_found(fn):
        def handler(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except NotFound as e:
                logger.warning(f'{str(fn.__name__)} not found')
                raise
            except Exception as e:
                logger.warning(str(e))
                raise
        return handler
    return wrap_not_found
