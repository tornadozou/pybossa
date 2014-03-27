# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2013 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.

from base import web, model, Fixtures, db, redis_flushall
from pybossa.auth import require
from pybossa.auth import token as token_authorization
from pybossa.model import TaskRun, Task
from nose.tools import assert_equal, assert_raises
from werkzeug.exceptions import Forbidden, Unauthorized
from mock import patch, Mock



class FakeCurrentUser:
    def __init__(self, user=None):
        if user:
            self.id = user.id
            self.admin = user.admin
        self.anonymous = user is None

    def is_anonymous(self):
        return self.anonymous


def setup_module():
    model.rebuild_db()


def teardown_module():
    db.session.remove()
    model.rebuild_db()
    redis_flushall()

def assert_not_raises(exception, call, *args, **kwargs):
    try:
        call(*args, **kwargs)
        assert True
    except exception as ex:
        assert False, str(ex)



class TestTaskrunCreateAuthorization:

    mock_anonymous = Mock()
    mock_anonymous.is_anonymous.return_value = True
    mock_authenticated = Mock(spec=model.User)
    mock_authenticated.is_anonymous.return_value = False
    mock_authenticated.admin = False
    mock_authenticated.id = 2
    mock_admin = Mock(spec=model.User)
    mock_admin.is_anonymous.return_value = False
    mock_admin.admin = True
    mock_admin.id = 1

    def setUp(self):
        model.rebuild_db()
        self.root, self.user1, self.user2 = Fixtures.create_users()
        db.session.add(self.root)
        db.session.add(self.user1)
        db.session.add(self.user2)
        self.app = Fixtures.create_app('')
        self.app.owner = self.root
        db.session.add(self.app)
        db.session.commit()
        self.task = model.Task(app_id=self.app.id, state='0', n_answers=10)
        self.task.app = self.app
        db.session.add(self.task)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        redis_flushall()




    def test_anonymous_user_create_first_taskrun(self):
        """Test anonymous user can create a taskrun for a given task if he
        hasn't already done it"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_anonymous:
                mock_is_anonymous.is_anonymous = Mock(return_value=True)

                taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_ip='127.0.0.0',
                                        info="some taskrun info")
                assert_not_raises(Exception,
                              getattr(require, 'taskrun').create,
                              taskrun)


    def test_anonymous_user_create_repeated_taskrun(self):
        """Test anonymous user cannot create a taskrun for a task to which
        he has previously posted a taskrun"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_anonymous:
                mock_is_anonymous.is_anonymous = Mock(return_value=True)

                taskrun1 = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_ip='127.0.0.0',
                                        info="some taskrun info")
                db.session.add(taskrun1)
                db.session.commit()
                taskrun2 = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_ip='127.0.0.0',
                                        info="a different taskrun info")
                assert_raises(Forbidden,
                            getattr(require, 'taskrun').create,
                            taskrun2)

                # But the user can still create taskruns for different tasks
                task2 = model.Task(app_id=self.app.id, state='0', n_answers=10)
                task2.app = self.app
                db.session.add(task2)
                db.session.commit()
                taskrun3 = model.TaskRun(app_id=self.app.id,
                                        task_id=task2.id,
                                        user_ip='127.0.0.0',
                                        info="some taskrun info")
                assert_not_raises(Exception,
                              getattr(require, 'taskrun').create,
                              taskrun3)


    def test_authenticated_user_create_first_taskrun(self):
        """Test authenticated user can create a taskrun for a given task if he
        hasn't already done it"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_authenticated:
                mock_is_authenticated.is_anonymous = Mock(return_value=False)
                mock_is_authenticated.admin = False
                mock_is_authenticated.id = self.user1.id

                taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_id=mock_is_authenticated.id,
                                        info="some taskrun info")
                assert_not_raises(Exception,
                              getattr(require, 'taskrun').create,
                              taskrun)

    def test_authenticated_user_create_repeated_taskrun(self):
        """Test authenticated user cannot create a taskrun for a task to which
        he has previously posted a taskrun"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_authenticated:
                mock_is_authenticated.is_anonymous = Mock(return_value=False)
                mock_is_authenticated.admin = False
                mock_is_authenticated.id = self.user1.id

                taskrun1 = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_id=mock_is_authenticated.id,
                                        info="some taskrun info")
                db.session.add(taskrun1)
                db.session.commit()
                taskrun2 = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_id=mock_is_authenticated.id,
                                        info="a different taskrun info")
                assert_raises(Forbidden, getattr(require, 'taskrun').create, taskrun2)

                # But the user can still create taskruns for different tasks
                task2 = model.Task(app_id=self.app.id, state='0', n_answers=10)
                task2.app = self.app
                db.session.add(task2)
                db.session.commit()
                taskrun3 = model.TaskRun(app_id=self.app.id,
                                        task_id=task2.id,
                                        user_id=mock_is_authenticated.id,
                                        info="some taskrun info")
                assert_not_raises(Exception,
                              getattr(require, 'taskrun').create,
                              taskrun3)


    def test_anonymous_user_read(self):
        """Test anonymous user can read any taskrun"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_anonymous:
                mock_is_anonymous.is_anonymous = Mock(return_value=True)

                anonymous_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_ip='127.0.0.0',
                                        info="some taskrun info")
                user_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_id=self.root.id,
                                        info="another taskrun info")

                assert_not_raises(Exception,
                              getattr(require, 'taskrun').read,
                              anonymous_taskrun)
                assert_not_raises(Exception,
                              getattr(require, 'taskrun').read,
                              user_taskrun)


    def test_authenticated_user_read(self):
        """Test authenticated user can read any taskrun"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_authenticated:
                mock_is_authenticated.is_anonymous = Mock(return_value=False)
                mock_is_authenticated.admin = False
                mock_is_authenticated.id = self.user1.id

                anonymous_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_ip='127.0.0.0',
                                        info="some taskrun info")
                other_users_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_id=self.root.id,
                                        info="a different taskrun info")
                own_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_id=mock_is_authenticated.id,
                                        info="another taskrun info")

                assert_not_raises(Exception,
                              getattr(require, 'taskrun').read,
                              anonymous_taskrun)
                assert_not_raises(Exception,
                              getattr(require, 'taskrun').read,
                              other_users_taskrun)
                assert_not_raises(Exception,
                              getattr(require, 'taskrun').read,
                              own_taskrun)


    def test_anonymous_user_update_anoymous_taskrun(self):
        """Test anonymous users cannot update an anonymously posted taskrun"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_anonymous:
                mock_is_anonymous.is_anonymous = Mock(return_value=True)

                anonymous_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_ip='127.0.0.0',
                                        info="some taskrun info")

                assert_raises(Unauthorized,
                              getattr(require, 'taskrun').update,
                              anonymous_taskrun)


    def test_authenticated_user_update_anonymous_taskrun(self):
        """Test authenticated users cannot update an anonymously posted taskrun"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_authenticated:
                mock_is_authenticated.is_anonymous = Mock(return_value=False)
                mock_is_authenticated.admin = False
                mock_is_authenticated.id = self.user1.id

                anonymous_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_ip='127.0.0.0',
                                        info="some taskrun info")

                assert_raises(Forbidden,
                              getattr(require, 'taskrun').update,
                              anonymous_taskrun)


    def test_admin_update_anonymous_taskrun(self):
        """Test admins cannot update anonymously posted taskruns"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_admin:
                mock_is_admin.is_anonymous = Mock(return_value=False)
                mock_is_admin.admin = True
                mock_is_admin.id = self.root.id

                anonymous_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_ip='127.0.0.0',
                                        info="some taskrun info")

                assert_raises(Forbidden,
                              getattr(require, 'taskrun').update,
                              anonymous_taskrun)


    def test_anonymous_user_update_user_taskrun(self):
        """Test anonymous user cannot update taskruns posted by authenticated users"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_anonymous:
                mock_is_anonymous.is_anonymous = Mock(return_value=True)

                user_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_id=self.root.id,
                                        info="some taskrun info")

                assert_raises(Unauthorized,
                              getattr(require, 'taskrun').update,
                              user_taskrun)


    def test_authenticated_user_update_other_users_taskrun(self):
        """Test authenticated user cannot update any taskrun"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_authenticated:
                mock_is_authenticated.is_anonymous = Mock(return_value=False)
                mock_is_authenticated.admin = False
                mock_is_authenticated.id = self.user1.id

                own_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_id=mock_is_authenticated.id,
                                        info="some taskrun info")
                other_users_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_id=self.root.id,
                                        info="a different taskrun info")

                assert_raises(Forbidden,
                              getattr(require, 'taskrun').update,
                              own_taskrun)
                assert_raises(Forbidden,
                              getattr(require, 'taskrun').update,
                              other_users_taskrun)


    def test_admin_update_user_taskrun(self):
        """Test admins cannot update taskruns posted by authenticated users"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_admin:
                mock_is_admin.is_anonymous = Mock(return_value=False)
                mock_is_admin.admin = True
                mock_is_admin.id = self.root.id

                user_taskrun = model.TaskRun(app_id=self.app.id,
                                        task_id=self.task.id,
                                        user_id=self.user1.id,
                                        info="some taskrun info")

                assert_raises(Forbidden,
                              getattr(require, 'taskrun').update,
                              user_taskrun)


    def test_anonymous_user_delete_anonymous_taskrun(self):
        """Test anonymous users cannot delete an anonymously posted taskrun"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_anonymous:
                with patch('pybossa.auth.taskrun.current_user') as mock_is_anonymous:
                    mock_is_anonymous.is_anonymous = Mock(return_value=True)

                    anonymous_taskrun = model.TaskRun(app_id=self.app.id,
                                            task_id=self.task.id,
                                            user_ip='127.0.0.0',
                                            info="some taskrun info")

                    assert_raises(Unauthorized,
                                  getattr(require, 'taskrun').delete,
                                  anonymous_taskrun)


    def test_authenticated_user_delete_anonymous_taskrun(self):
        """Test authenticated users cannot delete an anonymously posted taskrun"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_authenticated:
                mock_is_authenticated.is_anonymous = Mock(return_value=False)
                mock_is_authenticated.admin = False
                mock_is_authenticated.id = self.user1.id
                with patch('pybossa.auth.taskrun.current_user') as mock_is_authenticated:
                    anonymous_taskrun = model.TaskRun(app_id=self.app.id,
                                            task_id=self.task.id,
                                            user_ip='127.0.0.0',
                                            info="some taskrun info")

                    assert_raises(Forbidden,
                                  getattr(require, 'taskrun').delete,
                                  anonymous_taskrun)


    def test_admin_delete_anonymous_taskrun(self):
        """Test admins can delete anonymously posted taskruns"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_admin:
                with patch('pybossa.auth.taskrun.current_user') as mock_is_admin:
                    mock_is_admin.is_anonymous = Mock(return_value=False)
                    mock_is_admin.admin = True
                    mock_is_admin.id = self.root.id

                    anonymous_taskrun = model.TaskRun(app_id=self.app.id,
                                            task_id=self.task.id,
                                            user_ip='127.0.0.0',
                                            info="some taskrun info")

                    assert_not_raises(Exception,
                                  getattr(require, 'taskrun').delete,
                                  anonymous_taskrun)


    def test_anonymous_user_delete_user_taskrun(self):
        """Test anonymous user cannot delete taskruns posted by authenticated users"""
        with web.app.test_request_context('/'):
            with patch('pybossa.auth.current_user') as mock_is_anonymous:
                with patch('pybossa.auth.taskrun.current_user') as mock_is_anonymous:
                    mock_is_anonymous.is_anonymous = Mock(return_value=True)

                    user_taskrun = model.TaskRun(app_id=self.app.id,
                                            task_id=self.task.id,
                                            user_id=self.root.id,
                                            info="some taskrun info")

                    assert_raises(Unauthorized,
                              getattr(require, 'taskrun').delete,
                              user_taskrun)

    @patch('pybossa.auth.current_user', new=mock_authenticated)
    @patch('pybossa.auth.taskrun.current_user', new=mock_authenticated)
    def test_authenticated_user_delete_other_users_taskrun(self):
        """Test authenticated user cannot delete a taskrun if it was created
        by another authenticated user, but can delete his own taskruns"""
        with web.app.test_request_context('/'):
            own_taskrun = model.TaskRun(app_id=self.app.id,
                                    task_id=self.task.id,
                                    user_id=self.mock_authenticated.id,
                                    info="some taskrun info")
            other_users_taskrun = model.TaskRun(app_id=self.app.id,
                                    task_id=self.task.id,
                                    user_id=self.root.id,
                                    info="a different taskrun info")

            assert_not_raises(Exception,
                      getattr(require, 'taskrun').delete,
                      own_taskrun)
            assert_raises(Forbidden,
                      getattr(require, 'taskrun').delete,
                      other_users_taskrun)


    @patch('pybossa.auth.current_user', new=mock_admin)
    @patch('pybossa.auth.taskrun.current_user', new=mock_admin)
    def test_admin_delete_user_taskrun(self):
        """Test admins can delete taskruns posted by authenticated users"""
        with web.app.test_request_context('/'):
            user_taskrun = model.TaskRun(app_id=self.app.id,
                                    task_id=self.task.id,
                                    user=self.user1,
                                    info="some taskrun info")

            assert_not_raises(Exception,
                      getattr(require, 'taskrun').delete,
                      user_taskrun)



class TestTokenAuthorization:

    auth_providers = ('twitter', 'facebook', 'google')
    root, user1, user2 = Fixtures.create_users()


    def test_anonymous_user_delete(self):
        """Test anonymous user is not allowed to delete an oauth token"""
        token_authorization.current_user = FakeCurrentUser()

        for token in self.auth_providers:
            assert not token_authorization.delete(token)

    def test_authenticated_user_delete(self):
        """Test authenticated user is not allowed to delete an oauth token"""
        token_authorization.current_user = FakeCurrentUser(self.root)

        for token in self.auth_providers:
            assert not token_authorization.delete(token)

    def test_anonymous_user_create(self):
        """Test anonymous user is not allowed to create an oauth token"""
        token_authorization.current_user = FakeCurrentUser()

        for token in self.auth_providers:
            assert not token_authorization.create(token)

    def test_authenticated_user_create(self):
        """Test authenticated user is not allowed to create an oauth token"""
        token_authorization.current_user = FakeCurrentUser(self.root)

        for token in self.auth_providers:
            assert not token_authorization.create(token)

    def test_anonymous_user_update(self):
        """Test anonymous user is not allowed to update an oauth token"""
        token_authorization.current_user = FakeCurrentUser()

        for token in self.auth_providers:
            assert not token_authorization.update(token)

    def test_authenticated_user_update(self):
        """Test authenticated user is not allowed to update an oauth token"""
        token_authorization.current_user = FakeCurrentUser(self.root)

        for token in self.auth_providers:
            assert not token_authorization.update(token)

    def test_anonymous_user_read(self):
        """Test anonymous user is not allowed to read an oauth token"""
        token_authorization.current_user = FakeCurrentUser()

        for token in self.auth_providers:
            assert not token_authorization.read(token)

    def test_authenticated_user_read(self):
        """Test authenticated user is allowed to read his own oauth tokens"""
        token_authorization.current_user = FakeCurrentUser(self.root)

        for token in self.auth_providers:
            assert token_authorization.read(token)
