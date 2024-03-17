from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APIClient


from ohq.models import Course, Document, Semester, Membership

from ohq import vector_db

User = get_user_model()

class FileUploadAndVectorTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.semester = Semester.objects.create(year=2020, term=Semester.TERM_SUMMER)
        self.course = Course.objects.create(
            course_code="000", department="Penn Labs", semester=self.semester
        )
        self.ta = User.objects.create(username="head_ta")
        Membership.objects.create(course=self.course, user=self.ta, kind=Membership.KIND_HEAD_TA)

    def test_file_upload_and_vector_creation(self, mock_upsert):
        self.client.force_authenticate(user=self.user)
        file_content = b"This is a test document content."
        uploaded_file = SimpleUploadedFile("test.txt", file_content)

        response = self.client.post(
            f"/api/courses/{self.course.id}/vector_dbs/create",
            {"file": uploaded_file},
        )

        # Check if the document was created successfully
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Document.objects.count(), 1)

        document = Document.objects.first()

        # Test chunking and embedding
        chunks = vector_db.chunk_text(file_content.decode("utf-8"))
        self.assertEqual(len(chunks), 1)  # In this test, entire content is one chunk

        expected_embeddings = [vector_db.embed_vectors(chunk) for chunk in chunks]

        # Prepare metadata for chunks
        metadata = {
            "course": str(self.course),
            "document_name": vector_db.sanitize_to_ascii("test.txt"),
        }
        chunks_with_metadata = [(chunk, metadata) for chunk in chunks]

        vector_db.upload_vectors_with_metadata(chunks_with_metadata, batch_size=1)

        # Verify that upsert was called with the expected vectors and metadata
        mock_upsert.assert_called_once_with(
            vectors=[
                {
                    "id": f"test.txt_{i}",
                    "values": expected_embeddings[i],
                    "metadata": metadata,
                }
                for i in range(len(chunks))
            ]
        )

    def test_file_upload_empty_file(self):
        self.client.force_authenticate(user=self.user)
        
        uploaded_file = SimpleUploadedFile("empty.txt", b"")

        response = self.client.post(
            f"/api/courses/{self.course.id}/vector_dbs/create",
            {"file": uploaded_file},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.count(), 0)
