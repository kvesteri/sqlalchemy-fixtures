from collections import defaultdict
from sqlalchemy.orm import object_session
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.orm.properties import ColumnProperty
from sqlalchemy.util.langhelpers import symbol


class FixtureRegistry(object):
    session = None
    defaults = {}
    records = defaultdict(lambda: [])

    @classmethod
    def reset(cls):
        cls.records = defaultdict(lambda: [])

    @classmethod
    def set_defaults(cls, model, defaults):
        cls.defaults[model] = defaults

    @classmethod
    def create_fixture(cls, model, data={}, _save=True):
        defaults = cls.get_auto_defaults(model)

        if model in cls.defaults:
            defaults.update(cls.defaults[model])

        # set defaults
        for key, value in defaults.iteritems():
            data.setdefault(key, value)

        # create new record
        record = model(**data)
        if _save:
            cls.session.add(record)
            cls.session.commit()

        cls.add_record(model, record)
        return record

    @classmethod
    def add_record(cls, model, record):
        """Recursive function that adds record to fixture registries. Given
        record is added to its class registry as well as in all superclass
        registries that have __tablename__ present

        :param model:
        :param record:
        """
        for class_ in model.__bases__:
            cls.add_record(class_, record)

        if hasattr(model, '__tablename__'):
            cls.records[model].append(record)

    @classmethod
    def get_auto_defaults(cls, model):
        fields = set(model._sa_class_manager.values())
        defaults = {}
        for field in fields:
            property_ = field.property
            if isinstance(property_, ColumnProperty):
                if field.key == 'name':
                    defaults[field.key] = u'%s%d' % (
                        model.__name__, len(cls.records) + 1
                    )
            else:
                # RelationshipProperty

                column = property_.local_side[0]
                if (column.foreign_keys and not column.nullable and
                        not column.primary_key):
                    class_ = property_.mapper.class_
                    defaults[property_.key] = (
                        last_fixture(class_) or fixture(class_)
                    )
        return defaults


def last_fixture(cls):
    while FixtureRegistry.records[cls]:
        # fetch the last inserted record
        record = FixtureRegistry.records[cls][-1]
        state = record._sa_instance_state

        # if we find expired attributes, force load them all
        if state.expired_attributes:
            try:
                state(symbol('PASSIVE_OFF'))
            except ObjectDeletedError:
                state.deleted = True
        if state.deleted or not object_session(record):
            FixtureRegistry.records[cls].pop()
        else:
            return record


def fixture(cls, _save=True, **kwargs):
    return FixtureRegistry.create_fixture(cls, kwargs, _save=_save)
