import sqlalchemy as sa

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_fixtures import (
    FixtureRegistry, Lazy, fixture, last_fixture, new
)


engine = create_engine('sqlite:///:memory:')
Base = declarative_base(engine)
Session = sessionmaker(bind=engine)
session = Session()
FixtureRegistry.session = session


class Entity(Base):
    __tablename__ = 'entity'
    id = sa.Column(sa.Integer, primary_key=True)


class User(Entity):
    __tablename__ = 'user'

    id = sa.Column(sa.Integer, sa.ForeignKey(Entity.id), primary_key=True)
    name = sa.Column(sa.Unicode(255), index=True)
    email = sa.Column(sa.Unicode(255), unique=True)

    def __init__(self):
        # custom constructor
        pass


class Admin(User):
    pass


class Article(Base):
    __tablename__ = 'article'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Unicode(255), index=True)
    author_id = sa.Column(
        sa.Integer, sa.ForeignKey(User.id, ondelete='CASCADE'),
        nullable=False
    )
    author = sa.orm.relationship(
        User,
        backref='articles',
        primaryjoin=author_id == User.id
    )

    owner_id = sa.Column(
        sa.Integer, sa.ForeignKey(User.id, ondelete='CASCADE'),
        nullable=False
    )
    owner = sa.orm.relationship(
        User, primaryjoin=owner_id == User.id
    )  # relationship without backref


class TestFixtures(object):
    def setup_class(cls):
        Base.metadata.create_all()

    def teardown_class(cls):
        Base.metadata.drop_all()

    def teardown_method(self, method):
        tables = reversed(Base.metadata.sorted_tables)
        for table in tables:
            session.execute(table.delete())
        session.commit()
        FixtureRegistry.reset()

    def test_create_fixture(self):
        user = fixture(User)
        assert user.id
        assert user.name == 'User1'
        session.delete(user)
        session.commit()

    def test_last_fixture(self):
        user = fixture(User)
        assert user == last_fixture(User)

    def test_setting_defaults(self):
        FixtureRegistry.set_defaults(User, {'name': u'Someone'})
        user = fixture(User)
        assert user.name == u'Someone'

    def test_override_defaults(self):
        FixtureRegistry.set_defaults(User, {'name': u'Someone'})
        user = fixture(User, name=u'Someone else')
        assert user.name == u'Someone else'

    def test_lazy_value(self):
        FixtureRegistry.set_defaults(
            User, {
                'name': u'Someone',
                'email': Lazy(lambda obj: '%s@example.com' % obj.name.lower())
            }
        )
        user = fixture(User)
        assert user.email == 'someone@example.com'

    def test_automatically_sets_non_nullable_relations(self):
        article = fixture(Article)
        assert article.author.id

    def test_tries_to_use_last_fixture_for_relationship_fields(self):
        fixture(User, name=u'someone')
        article = fixture(Article)
        assert article.author.name == u'someone'
        assert article.owner.name == u'someone'

    def test_supports_deep_inheritance(self):
        admin = fixture(Admin)
        assert last_fixture(User) == admin
        assert last_fixture(Admin) == admin
        assert last_fixture(Entity) == admin

    def test_using_new_does_not_commit_related_records(self):
        new(Article)
        assert not session.query(User).all()  # should not create user
