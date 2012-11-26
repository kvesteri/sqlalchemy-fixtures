import sqlalchemy as sa

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_fixtures import FixtureRegistry, fixture, last_fixture


engine = create_engine('sqlite:///:memory:')
Base = declarative_base(engine)
Session = sessionmaker(bind=engine)
session = Session()
FixtureRegistry.session = session


class User(Base):
    __tablename__ = 'user'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Unicode(255), index=True)


class Article(Base):
    __tablename__ = 'article'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Unicode(255), index=True)
    author_id = sa.Column(
        sa.Integer, sa.ForeignKey(User.id, ondelete='CASCADE'),
        nullable=False
    )
    author = sa.orm.relationship(User)


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

    def test_create_fixture(self):
        user = fixture(User)
        assert user.id
        assert user.name == 'User1'
        session.delete(user)
        session.commit()

    def test_last_fixture(self):
        user = fixture(User)
        assert user == last_fixture(User)

    def test_override_defaults(self):
        user = fixture(User, name=u'someone')
        assert user.name == u'someone'

    def test_automatically_sets_non_nullable_relations(self):
        article = fixture(Article)
        assert article.author.id

    def test_tries_to_use_last_fixture_for_relationship_fields(self):
        fixture(User, name=u'someone')
        article = fixture(Article)
        assert article.author.name == u'someone'
