SQLAlchemy-Fixtures
===================

SQLAlchemy-Fixtures is a python package that provides functional fixtures for
SQLAlchemy based models.

QuickStart
----------

At the heart of SQLAlchemy-Fixtures there are two functions: fixture and last_fixture.
Function fixture is used for constructing fixtures from models and last_fixture is used
for getting the last created fixture for given model.

Consider the following model definition:

::

    import sqlalchemy as sa
    from sqlalchemy import create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    engine = create_engine('sqlite:///:memory:')
    Base = declarative_base(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    class User(Base):
        __tablename__ = 'user'

        id = sa.Column(sa.BigInteger, autoincrement=True, primary_key=True)
        name = sa.Column(sa.Unicode(100))
        email = sa.Column(sa.Unicode(255))


Now creating new fixtures is as easy as: ::

    from sqlalchemy_fixture import fixture

    user = fixture(User, name=u'someone', email=u'john@example.com')
    last_fixture(User) == user


Most of the time you will want your models to contain some default values. This can be
achieved by using FixtureRegistry.set_defaults function
::

    from sqlalchemy_fixture import fixture, last_fixture

    FixtureRegistry.set_defaults(User, {'name': 'someone'})

    user = fixture(User)
    user.name  # someone

    last_fixture(User) == user
