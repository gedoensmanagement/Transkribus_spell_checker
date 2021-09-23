"""empty message

Revision ID: 847f24db2b48
Revises: 
Create Date: 2021-09-14 20:46:44.700753

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '847f24db2b48'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('password', sa.String(length=100), nullable=False),
    sa.Column('colcache', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('censorship',
    sa.Column('uuid', sa.String(length=32), nullable=False),
    sa.Column('cts', sa.String(length=128), nullable=False),
    sa.Column('source', sa.String(length=56), nullable=True),
    sa.Column('target', sa.String(length=56), nullable=True),
    sa.Column('html', sa.Text(length=65000), nullable=True),
    sa.Column('comment', sa.Text(length=2048), nullable=True),
    sa.Column('userid', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['userid'], ['user.id'], ),
    sa.PrimaryKeyConstraint('uuid')
    )
    op.create_table('dictionary',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('word', sa.String(length=40), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('userid', sa.Integer(), nullable=False),
    sa.Column('cts', sa.String(length=30), nullable=True),
    sa.Column('action', sa.String(length=15), nullable=True),
    sa.Column('flag', sa.String(length=15), nullable=True),
    sa.Column('comment', sa.String(length=160), nullable=True),
    sa.ForeignKeyConstraint(['userid'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('locker',
    sa.Column('pageid', sa.String(length=30), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('userid', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['userid'], ['user.id'], ),
    sa.PrimaryKeyConstraint('pageid')
    )
    op.create_table('printers_error',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('userid', sa.Integer(), nullable=False),
    sa.Column('cts', sa.String(length=30), nullable=True),
    sa.Column('pattern', sa.String(length=30), nullable=False),
    sa.Column('replacement', sa.String(length=40), nullable=False),
    sa.Column('comment', sa.String(length=160), nullable=True),
    sa.ForeignKeyConstraint(['userid'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('tag',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('userid', sa.Integer(), nullable=False),
    sa.Column('tag', sa.String(length=144), nullable=False),
    sa.ForeignKeyConstraint(['userid'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('censoredword',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cts', sa.String(length=128), nullable=False),
    sa.Column('type', sa.String(length=6), nullable=True),
    sa.Column('parent', sa.String(length=32), nullable=False),
    sa.Column('reference', sa.String(length=128), nullable=True),
    sa.ForeignKeyConstraint(['parent'], ['censorship.uuid'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('comment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('userid', sa.Integer(), nullable=False),
    sa.Column('comment', sa.Text(length=2048), nullable=False),
    sa.Column('cts', sa.String(length=30), nullable=True),
    sa.Column('flag', sa.String(length=15), nullable=True),
    sa.Column('tagid', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['tagid'], ['tag.id'], ),
    sa.ForeignKeyConstraint(['userid'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('comment')
    op.drop_table('censoredword')
    op.drop_table('tag')
    op.drop_table('printers_error')
    op.drop_table('locker')
    op.drop_table('dictionary')
    op.drop_table('censorship')
    op.drop_table('user')
    # ### end Alembic commands ###
