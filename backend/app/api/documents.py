from datetime import date

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from app.dependencies import current_patient, document_service
from app.schemas.documents import DocumentList, DocumentResponse, DocumentType
from app.services.documents import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload(
    file: UploadFile = File(...),
    document_type: DocumentType | None = Form(None),
    document_date: date | None = Form(None),
    patient: dict = Depends(current_patient),
    service: DocumentService = Depends(document_service),
):
    return await service.upload(patient["_id"], file, document_type, document_date)


@router.get("", response_model=DocumentList)
async def list_documents(patient: dict = Depends(current_patient), service=Depends(document_service)):
    return DocumentList(documents=await service.list(patient["_id"]))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str, patient: dict = Depends(current_patient), service=Depends(document_service)
):
    return await service.get(patient["_id"], document_id)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str, patient: dict = Depends(current_patient), service=Depends(document_service)
):
    await service.delete(patient["_id"], document_id)
    return Response(status_code=204)
