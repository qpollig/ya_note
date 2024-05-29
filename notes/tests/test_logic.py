from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse
from pytils.translit import slugify

from notes.forms import WARNING
from notes.models import Note
from notes.tests.test_routes import User


class TestNotesCreation(TestCase):
    URL_USERS_LOGIN = reverse('users:login')
    URL_NOTES_SUCCESS = reverse('notes:success')
    URL_NOTES_ADD = reverse('notes:add')

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='Автор')
        cls.reader = User.objects.create(username='Читатель простой')
        cls.author_logged = Client()
        cls.reader_logged = Client()
        cls.author_logged.force_login(cls.author)
        cls.reader_logged.force_login(cls.reader)
        cls.note = Note.objects.create(
            title='Заголовок',
            text='Заметка',
            slug='slug-001',
            author=cls.author,
        )
        cls.form_data = {
            'title': 'Новый заголовок',
            'text': 'Новый текст',
            'slug': 'new-slug'
        }
        cls.NOTES_COUNT = Note.objects.count()
        cls.URL_NOTES_EDIT = reverse('notes:edit', args=(cls.note.slug,))
        cls.URL_NOTES_DELETE = reverse('notes:delete', args=(cls.note.slug,))

    def test_user_can_create_note(self):
        # Залогиненный пользователь может создать заметку
        response = self.author_logged.post(
            self.URL_NOTES_ADD,
            data=self.form_data
        )
        self.assertRedirects(response, self.URL_NOTES_SUCCESS)
        self.assertEqual(Note.objects.count(), self.NOTES_COUNT + 1)
        new_note = Note.objects.order_by('id').last()
        self.assertEqual(new_note.title, self.form_data['title'])
        self.assertEqual(new_note.text, self.form_data['text'])
        self.assertEqual(new_note.slug, self.form_data['slug'])
        self.assertEqual(new_note.author, self.author)

    def test_anonymous_user_cant_create_note(self):
        response = self.client.post(self.URL_NOTES_ADD, data=self.form_data)
        expected_url = f'{self.URL_USERS_LOGIN}?next={self.URL_NOTES_ADD}'
        self.assertRedirects(response, expected_url)
        self.assertEqual(Note.objects.count(), self.NOTES_COUNT)

    def test_slug(self):
        self.form_data['slug'] = self.note.slug
        response = self.author_logged.post(
            self.URL_NOTES_ADD,
            data=self.form_data
        )
        self.assertFormError(
            response,
            'form',
            'slug',
            errors=(self.note.slug + WARNING)
        )
        self.assertEqual(Note.objects.count(), self.NOTES_COUNT)

    def test_slug_create_pytils(self):
        self.form_data.pop('slug')
        response = self.author_logged.post(
            self.URL_NOTES_ADD,
            data=self.form_data
        )
        self.assertRedirects(response, self.URL_NOTES_SUCCESS)
        self.assertEqual(Note.objects.count(), self.NOTES_COUNT + 1)
        new_note = Note.objects.order_by('id').last()
        expected_slug = slugify(self.form_data['title'])
        self.assertEqual(new_note.slug, expected_slug)

    def test_author_can_edit_note(self):
        response = self.author_logged.post(
            self.URL_NOTES_EDIT,
            data=self.form_data
        )
        self.assertRedirects(response, self.URL_NOTES_SUCCESS)
        self.assertEqual(Note.objects.count(), self.NOTES_COUNT)
        self.assertEqual(Note.objects.get().title, self.form_data['title'])
        self.assertEqual(Note.objects.get().text, self.form_data['text'])
        self.assertEqual(Note.objects.get().slug, self.form_data['slug'])

    def test_other_user_cant_edit_note(self):
        response = self.reader_logged.post(
            self.URL_NOTES_EDIT,
            data=self.form_data
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(self.note.title, Note.objects.get(id=self.note.id).title)
        self.assertEqual(self.note.text, Note.objects.get(id=self.note.id).text)
        self.assertEqual(self.note.slug, Note.objects.get(id=self.note.id).slug)

    def test_author_can_delete_note(self):
        response = self.author_logged.post(self.URL_NOTES_DELETE)
        self.assertRedirects(response, self.URL_NOTES_SUCCESS)
        self.assertEqual(Note.objects.count(), self.NOTES_COUNT - 1)

    def test_other_user_cant_delete_note(self):
        response = self.reader_logged.post(self.URL_NOTES_DELETE)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(Note.objects.count(), self.NOTES_COUNT)
