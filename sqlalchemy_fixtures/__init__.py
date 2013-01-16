from collections import defaultdict
from sqlalchemy.orm import object_session
from sqlalchemy.orm.exc import ObjectDeletedError, DetachedInstanceError
from sqlalchemy.orm.properties import ColumnProperty
from sqlalchemy.util.langhelpers import symbol


class FixtureRegistry(object):
    session = None
    defaults = {}
    records = defaultdict(lambda: [])

    @classmethod
    def reset(cls):
        """
        Reset the internal record registry
        """
        cls.records = defaultdict(lambda: [])

    @classmethod
    def set_defaults(cls, model, defaults):
        """
        Set data defaults for given model

        :param model: sqlalchemy declarative model class
        :param defaults: key-value dictionary that is passed as attribute
            default values for given model fixture, keys as attribute names and
            values as attribute values
        """
        cls.defaults[model] = defaults

    @classmethod
    def create_fixture(cls, model, data={}, _save=True):
        """
        Create a fixture for given model based on given data and model based
        defaults. If _save=True this method also commits the database session.

        :param model: sqlalchemy declarative model class
        :param data: key-value dictionary that is passed as attribute values
            for newly created fixture, keys as attribute names and values
            as attribute values
        :param _save: whether or not to save created record
        """
        defaults = cls.get_auto_defaults(model, _save=_save)

        if model in cls.defaults:
            defaults.update(cls.defaults[model])

        # set defaults
        for key, value in defaults.iteritems():
            data.setdefault(key, value)

        # create new record and assign data values
        record = model()
        lazy_properties = {}
        for key, value in data.items():
            if isinstance(value, Lazy):
                lazy_properties[key] = value
            setattr(record, key, value)

        for key, value in lazy_properties.items():
            setattr(record, key, value(record))

        if _save:
            cls.session.add(record)
            cls.session.commit()

        cls.add_record(model, record)
        return record

    @classmethod
    def add_record(cls, model, record):
        """Recursive function that adds record to fixture registries. Given
        record is added to its class registry as well as in all superclass
        registries that have __tablename__ present.

        :param model: model class that represents record list key
        :param record: record to be added
        """
        for class_ in model.__bases__:
            cls.add_record(class_, record)

        if hasattr(model, '__tablename__'):
            cls.records[model].append(record)

    @classmethod
    def get_auto_defaults(cls, model, _save=True):
        """
        Returns the automatically constructed default values for given model.
        By default sqlalchemy-fixtures only sets default values for
        non-nullable relations.

        :param model: Model to construct the default values for
        :param _save: whether or not to save the related records
        """
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
                        last_fixture(class_) or fixture(class_, _save=_save)
                    )
        return defaults


class Lazy(object):
    def __init__(self, callable_=None):
        self.callable = callable_

    def __call__(self, obj, *args, **kwargs):
        return self.callable(obj)


def last_fixture(model):
    """
    Return the last created and non-deleted fixture for given model. If no
    non-deleted record was found this function returns None.

    :param model: sqlalchemy declarative model
    """
    while FixtureRegistry.records[model]:
        # fetch the last inserted record
        record = FixtureRegistry.records[model][-1]
        state = record._sa_instance_state
        detached = False
        # if we find expired attributes, force load them all
        if state.expired_attributes:
            try:
                state(symbol('PASSIVE_OFF'))
            except DetachedInstanceError:
                detached = True
            except ObjectDeletedError:
                state.deleted = True
        if detached or state.deleted or not object_session(record):
            FixtureRegistry.records[model].pop()
        else:
            return record


def fixture(model, _save=True, **kwargs):
    """
    Create a fixture for given model based on given data and model based
    defaults. If _save=True this method also commits the database session.

    :param model: sqlalchemy declarative model class
    :param _save: whether or not to save created record
    :param **kwargs: key-value dictionary that is passed as attribute values
        for newly created fixture, keys as attribute names and values
        as attribute values
    """
    return FixtureRegistry.create_fixture(model, kwargs, _save=_save)


def new(model, **kwargs):
    """
    Create a fixture for given model based on given data and model based
    defaults. Compared to fixture function this function does not add the
    created object into session.

    :param model: sqlalchemy declarative model class
    :param **kwargs: key-value dictionary that is passed as attribute values
        for newly created fixture, keys as attribute names and values
        as attribute values
    """
    return FixtureRegistry.create_fixture(model, kwargs, _save=False)
