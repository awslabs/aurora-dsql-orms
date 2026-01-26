# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import uuid

import pytest
from tortoise import Tortoise, fields
from tortoise.expressions import Q
from tortoise.fields.relational import ReverseRelation
from tortoise.functions import Avg, Count, Max, Min, Sum
from tortoise.models import Model

from tests.conftest import BACKENDS


class Author(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100)
    books: ReverseRelation["Book"]

    class Meta:
        table = "test_author"


class Book(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    title = fields.CharField(max_length=200)
    price = fields.IntField()
    author = fields.ForeignKeyField("models.Author", related_name="books")

    class Meta:
        table = "test_book"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestJoins:
    async def test_select_related(self, backend):
        author = await Author.create(name="Alice")
        await Book.create(title="Book1", price=10, author=author)
        book = await Book.all().select_related("author").first()
        assert book is not None
        assert book.author.name == "Alice"

    async def test_prefetch_related(self, backend):
        author = await Author.create(name="Bob")
        await Book.create(title="B1", price=5, author=author)
        await Book.create(title="B2", price=15, author=author)
        fetched = await Author.all().prefetch_related("books").first()
        assert fetched is not None
        assert len(fetched.books) == 2

    async def test_filter_across_relation(self, backend):
        a1 = await Author.create(name="Carol")
        a2 = await Author.create(name="Dave")
        await Book.create(title="C1", price=10, author=a1)
        await Book.create(title="D1", price=20, author=a2)
        books = await Book.filter(author__name="Carol").all()
        assert len(books) == 1
        assert books[0].title == "C1"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestAggregations:
    async def test_count(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="B1", price=10, author=author)
        await Book.create(title="B2", price=20, author=author)
        result = await Book.all().annotate(cnt=Count("id")).values("cnt")
        assert result[0]["cnt"] == 2

    async def test_sum(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="B1", price=10, author=author)
        await Book.create(title="B2", price=20, author=author)
        result = await Book.all().annotate(total=Sum("price")).values("total")
        assert result[0]["total"] == 30

    async def test_avg(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="B1", price=10, author=author)
        await Book.create(title="B2", price=20, author=author)
        result = await Book.all().annotate(average=Avg("price")).values("average")
        assert result[0]["average"] == 15

    async def test_min_max(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="B1", price=5, author=author)
        await Book.create(title="B2", price=25, author=author)
        result = await Book.all().annotate(lo=Min("price"), hi=Max("price")).values("lo", "hi")
        assert result[0]["lo"] == 5
        assert result[0]["hi"] == 25

    async def test_group_by(self, backend):
        a1 = await Author.create(name="A1")
        a2 = await Author.create(name="A2")
        await Book.create(title="B1", price=10, author=a1)
        await Book.create(title="B2", price=20, author=a1)
        await Book.create(title="B3", price=30, author=a2)
        result = (
            await Book.all()
            .annotate(cnt=Count("id"))
            .group_by("author_id")
            .values("author_id", "cnt")
        )
        counts = {r["author_id"]: r["cnt"] for r in result}
        assert counts[a1.id] == 2
        assert counts[a2.id] == 1


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestFiltering:
    async def test_comparison_operators(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="Cheap", price=5, author=author)
        await Book.create(title="Mid", price=15, author=author)
        await Book.create(title="Expensive", price=25, author=author)
        assert await Book.filter(price__gt=10).count() == 2
        assert await Book.filter(price__gte=15).count() == 2
        assert await Book.filter(price__lt=15).count() == 1
        assert await Book.filter(price__lte=15).count() == 2

    async def test_in_operator(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="A", price=1, author=author)
        await Book.create(title="B", price=2, author=author)
        await Book.create(title="C", price=3, author=author)
        result = await Book.filter(title__in=["A", "C"]).all()
        assert len(result) == 2

    async def test_contains_icontains(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="Hello World", price=1, author=author)
        await Book.create(title="Goodbye", price=2, author=author)
        assert await Book.filter(title__contains="World").count() == 1
        assert await Book.filter(title__icontains="hello").count() == 1

    async def test_startswith_endswith(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="Python Guide", price=1, author=author)
        await Book.create(title="Java Guide", price=2, author=author)
        assert await Book.filter(title__startswith="Python").count() == 1
        assert await Book.filter(title__endswith="Guide").count() == 2

    async def test_isnull(self, backend):
        await Author.create(name="Named")
        assert await Author.filter(name__isnull=True).count() == 0
        assert await Author.filter(name__isnull=False).count() == 1

    async def test_q_objects_or(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="A", price=5, author=author)
        await Book.create(title="B", price=50, author=author)
        result = await Book.filter(Q(title="A") | Q(price__gt=40)).all()
        assert len(result) == 2

    async def test_q_objects_and(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="Match", price=100, author=author)
        await Book.create(title="Match", price=5, author=author)
        await Book.create(title="NoMatch", price=100, author=author)
        result = await Book.filter(Q(title="Match") & Q(price__gt=50)).all()
        assert len(result) == 1

    async def test_not_filter(self, backend):
        author = await Author.create(name="Test")
        await Book.create(title="Keep", price=10, author=author)
        await Book.create(title="Skip", price=20, author=author)
        result = await Book.filter(~Q(title="Skip")).all()
        assert len(result) == 1
        assert result[0].title == "Keep"


@pytest.mark.asyncio
@pytest.mark.use_schemas
@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestParameterizedQueries:
    async def test_raw_sql_with_params(self, backend):
        author = await Author.create(name="RawTest")
        await Book.create(title="RawBook", price=99, author=author)
        conn = Tortoise.get_connection("default")
        placeholder = "%s" if backend == "psycopg" else "$1"
        result = await conn.execute_query(
            f"SELECT title FROM test_book WHERE price = {placeholder}", [99]
        )
        assert result[1][0]["title"] == "RawBook"

    async def test_raw_sql_multiple_params(self, backend):
        author = await Author.create(name="Multi")
        await Book.create(title="Target", price=50, author=author)
        await Book.create(title="Other", price=100, author=author)
        conn = Tortoise.get_connection("default")
        if backend == "psycopg":
            query = "SELECT title FROM test_book WHERE price > %s AND price < %s"
        else:
            query = "SELECT title FROM test_book WHERE price > $1 AND price < $2"
        result = await conn.execute_query(query, [40, 60])
        assert len(result[1]) == 1
        assert result[1][0]["title"] == "Target"
