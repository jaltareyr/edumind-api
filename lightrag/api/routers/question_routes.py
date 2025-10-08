from __future__ import annotations

import io
import base64
import pandas as pd
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Question as QuestionModel, QuestionOptionVariant as VariantModel
from ..utils_api import get_combined_auth_dependency
from ascii_colors import trace_exception

import xml.etree.ElementTree as ET
import zipfile
from fastapi.responses import StreamingResponse
import uuid

def generate_ident(prefix="q"):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def convert_questions_to_qti_zip(formatted_data, quiz_name):
    ET.register_namespace("", "http://www.imsglobal.org/xsd/ims_qtiasiv1p2")

    root = ET.Element(
        'questestinterop',
        {
            "xmlns": "http://www.imsglobal.org/xsd/ims_qtiasiv1p2",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://www.imsglobal.org/xsd/ims_qtiasiv1p2 http://www.imsglobal.org/xsd/ims_qtiasiv1p2p1.xsd"
        }
    )
    assessment = ET.SubElement(
        root, 'assessment', ident=generate_ident("quiz"), title=quiz_name)
    qtimetadata = ET.SubElement(assessment, 'qtimetadata')
    qtimetadatafield = ET.SubElement(qtimetadata, 'qtimetadatafield')
    ET.SubElement(qtimetadatafield, 'fieldlabel').text = "cc_maxattempts"
    ET.SubElement(qtimetadatafield, 'fieldentry').text = "1"
    section = ET.SubElement(assessment, 'section',
                            ident=generate_ident("section"))

    for index, row in enumerate(formatted_data):
        item_id = generate_ident("q")
        question_type = row["Type"]
        point_value = str(row["Points"])
        max_score = "100"
        question_body = row["Question"]
        correct_answers = row["CorrectAnswer"].split(';')
        answer_choices = [
            row.get(f"option {chr(i + 65)}", "") for i in range(5)
        ]
        valid_answers = [(idx + 1, choice) for idx,
                         choice in enumerate(answer_choices) if choice.strip()]

        item = ET.SubElement(section, 'item', ident=item_id,
                             title=f"Question {index+1}")

        itemmetadata = ET.SubElement(item, 'itemmetadata')
        qtimetadata = ET.SubElement(itemmetadata, 'qtimetadata')

        q_type_str = "multiple_choice_question" if question_type == "MC" else "multiple_answers_question"
        qtimetadatafield = ET.SubElement(qtimetadata, 'qtimetadatafield')
        ET.SubElement(qtimetadatafield, 'fieldlabel').text = "question_type"
        ET.SubElement(qtimetadatafield, 'fieldentry').text = q_type_str

        qtimetadatafield = ET.SubElement(qtimetadata, 'qtimetadatafield')
        ET.SubElement(qtimetadatafield, 'fieldlabel').text = "points_possible"
        ET.SubElement(qtimetadatafield, 'fieldentry').text = point_value

        qtimetadatafield = ET.SubElement(qtimetadata, 'qtimetadatafield')
        ET.SubElement(qtimetadatafield,
                      'fieldlabel').text = "assessment_question_identifierref"
        ET.SubElement(qtimetadatafield, 'fieldentry').text = item_id

        presentation = ET.SubElement(item, 'presentation')
        material = ET.SubElement(presentation, 'material')
        mattext = ET.SubElement(material, 'mattext', texttype="text/html")
        mattext.text = question_body

        response_lid = ET.SubElement(
            presentation, 'response_lid', ident="response1")
        response_lid.set(
            "rcardinality", "Multiple" if question_type == "MR" else "Single")
        render_choice = ET.SubElement(response_lid, 'render_choice')

        # Track option index -> generated option_id
        option_index_to_id = {}
        for idx, option_text in valid_answers:
            option_id = generate_ident("a")
            option_index_to_id[str(idx)] = option_id
            response_label = ET.SubElement(
                render_choice, 'response_label', ident=option_id)
            material = ET.SubElement(response_label, 'material')
            mattext = ET.SubElement(material, 'mattext', texttype="text/plain")
            mattext.text = option_text

        # Set up scoring logic
        resprocessing = ET.SubElement(item, 'resprocessing')
        outcomes = ET.SubElement(resprocessing, "outcomes")
        decvar = ET.SubElement(outcomes, "decvar", maxvalue=max_score,
                               minvalue="0", varname="SCORE", vartype="Decimal")
        respcondition = ET.SubElement(
            resprocessing, 'respcondition', attrib={"continue": "No"})
        conditionvar = ET.SubElement(respcondition, 'conditionvar')

        # MR = all correct must be checked (AND), MC = just one
        # The correct_answers from CSV might be e.g. "1,3" or "2"
        # We split by ";" for multi-part answers (if any), or use just first
        correct_option_ids = []
        for correct_option in correct_answers:
            correct_option = correct_option.strip()
            if correct_option:
                # Sometimes CSV gives "1,3" for two answers
                for opt in correct_option.split(","):
                    opt = opt.strip()
                    if opt and opt in option_index_to_id:
                        correct_option_ids.append(option_index_to_id[opt])

        if question_type == "MR":
            and_elem = ET.SubElement(conditionvar, 'and')
            for correct_option_id in correct_option_ids:
                varequal = ET.SubElement(
                    and_elem, 'varequal', respident="response1")
                varequal.text = correct_option_id
        else:  # MC
            for correct_option_id in correct_option_ids:
                varequal = ET.SubElement(
                    conditionvar, 'varequal', respident="response1")
                varequal.text = correct_option_id

        setvar = ET.SubElement(respcondition, "setvar",
                               action="Set", varname="SCORE")
        setvar.text = max_score

    # Serialize XML to memory
    qti_buffer = io.BytesIO()
    ET.ElementTree(root).write(
        qti_buffer, encoding='ISO-8859-1', xml_declaration=True)
    qti_bytes = qti_buffer.getvalue()

    # --- 2. Zip the QTI file in memory ---
    timestamp = datetime.now().strftime("%m%d%y%H%M%S")
    file_name = f"questions_{timestamp}.xml"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(file_name, qti_bytes)
    zip_bytes = zip_buffer.getvalue()

    return zip_bytes


async def export_questions_controller(payload):
    try:
        filename = payload.filename
        fileformat = payload.fileformat
        questions = payload.questions

        formatted_data = []
        for item in questions:
            qtype = "MR" if len(item.correct_options) > 1 else "MC"
            corret_answers = ",".join([str(i + 1)
                                      for i in item.correct_options])
            options = item.options if item.options else []

            row = {
                "Type": qtype,
                "Unused": "",
                "Points": "1",
                "Question": item.question,
                "CorrectAnswer": corret_answers,
            }
            for i in range(5):
                row[f"option {chr(i + 65)}"] = item.options[i] if i < len(options) else ""
            formatted_data.append(row)

        if fileformat == "csv":
            csv_buffer = io.StringIO()
            df = pd.DataFrame(formatted_data)
            df.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue().encode('utf-8')
            csv_base64 = base64.b64encode(csv_bytes).decode('utf-8')
            return {
                "fileformat": fileformat,
                "filedata": csv_base64
            }

        if fileformat == "qti":
            # Generate the QTI zip in-memory
            zip_bytes = convert_questions_to_qti_zip(
                formatted_data, quiz_name=filename)
            zip_base64 = base64.b64encode(zip_bytes).decode('utf-8')
            return {
                "fileformat": fileformat,
                "filedata": zip_base64
            }

        else:
            return {
                "fileformat": fileformat,
                "filedata": "Unsupported file format"
            }

    except Exception as e:
        logging.error(f"Error in export_questions_controller: {e!r}")
        raise

def create_questions(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    project_id: Optional[str],
    questions: List[Dict[str, Any]],
) -> List[str]:
    ids: List[str] = []
    for q in questions:
        qid = str(uuid4())
        obj = QuestionModel(
            id=qid,
            user_id=user_id,
            session_id=session_id,
            project_id=project_id,
            question_text=q.get("question", ""),
            options=q.get("options", []) or [],
            correct_answers=q.get("correct_options", []) or [],
            difficulty_level=q.get("difficulty_level") or None,
            tags=q.get("tags", []) or [],
            source=q.get("source") or "",
            type=q.get("type") or "",
        )
        db.add(obj)
        ids.append(qid)
    db.commit()
    return ids

# ---------------------- Schemas ----------------------

class QuestionVariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    question_id: str
    difficulty_level: Optional[str] = None
    options: List[str] = []
    correct_answers: List[int] = []
    rationale: str
    created_at: datetime
    updated_at: datetime

class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    question_text: str
    options: List[str] = []
    correct_answers: List[int] = []
    difficulty_level: Optional[str] = None
    tags: List[str] = []
    source: Optional[str] = None
    type: Optional[str] = None
    isApproved: bool = False
    isArchived: bool = False
    created_at: datetime
    updated_at: datetime
    variants: List[QuestionVariantOut] = []

class CreateQuestionItem(BaseModel):
    user_id: str
    session_id: str
    project_id: Optional[str] = None
    question: str = Field(alias="question_text")
    options: List[str] = []
    correct_options: List[int] = Field(default_factory=list, alias="correct_answers")
    difficulty_level: Optional[str] = None
    tags: List[str] = []
    source: Optional[str] = None
    type: Optional[str] = None

    # Accept both old and new keys seamlessly
    def to_model_kwargs(self) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "project_id": self.project_id,
            "question_text": self.question,
            "options": self.options or [],
            "correct_answers": self.correct_options or [],
            "difficulty_level": self.difficulty_level,
            "tags": self.tags or [],
            "source": self.source or "",
            "type": self.type or "",
        }

class CreateQuestionsOut(BaseModel):
    success: bool = True
    message: str = "Questions created."
    ids: List[str]

class ListOut(BaseModel):
    success: bool = True
    total: int
    page: int
    pageSize: int
    questions: List[QuestionOut]

class ItemOut(BaseModel):
    success: bool = True
    question: QuestionOut

class SuccessOut(BaseModel):
    success: bool = True
    message: str

class PatchQuestionIn(BaseModel):
    # Partial update fields (state + content)
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answers: Optional[List[int]] = None
    difficulty_level: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    type: Optional[str] = None
    isApproved: Optional[bool] = None
    isArchived: Optional[bool] = None
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None  # if you want to allow reassignment

class BulkPatchIn(BaseModel):
    ids: List[str]
    patch: PatchQuestionIn

class ExportQuestion(BaseModel):
    question: str
    options: List[str] = []
    correct_options: List[int] = []

class ExportQuestionsIn(BaseModel):
    filename: str = "questions_export"
    fileformat: str = Field("csv", description="csv or qti")
    questions: List[ExportQuestion]

def create_question_routes(api_key: Optional[str] = None) -> APIRouter:
    router = APIRouter(prefix="/questions", tags=["questions"])
    auth = get_combined_auth_dependency(api_key)

    # --- POST /v1/questions (single or bulk create)
    @router.post("/", response_model=CreateQuestionsOut, dependencies=[Depends(auth)])
    def create_questions(
        payload: Union[CreateQuestionItem, List[CreateQuestionItem]] = Body(...),
        db: Session = Depends(get_db),
    ):
        try:
            items = payload if isinstance(payload, list) else [payload]
            ids: List[str] = []
            for item in items:
                kwargs = item.to_model_kwargs()
                obj = QuestionModel(**kwargs)
                db.add(obj)
                ids.append(kwargs["id"])
            db.commit()
            return CreateQuestionsOut(ids=ids)
        except Exception as e:
            trace_exception(e)
            raise HTTPException(status_code=500, detail=f"Failed to create questions: {e}")

    # --- GET /v1/questions (list + filters)
    @router.get("/", response_model=ListOut, dependencies=[Depends(auth)])
    def list_questions(
        db: Session = Depends(get_db),
        # Filters
        user_id: Optional[str] = Query(None),
        session_id: Optional[str] = Query(None),
        project_id: Optional[str] = Query(None),
        type: Optional[str] = Query(None, description="Filter by question type ('mcq' or 'multiple_response' or 'true_false')"),
        hasVariants: Optional[bool] = Query(None, description="Filter questions that have variants"),
        isApproved: Optional[bool] = Query(None),
        isArchived: Optional[bool] = Query(False),
        q: Optional[str] = Query(None, description="Full-text search on question_text (simple ILIKE)"),
        # Pagination & sorting
        page: int = Query(1, ge=1),
        pageSize: int = Query(50, ge=1, le=200),
        sort: str = Query("updated_at"),
        order: str = Query("desc", regex="^(asc|desc)$"),
    ):
        try:
            stmt = select(QuestionModel)
            # Filters
            where = []
            if user_id:
                where.append(QuestionModel.user_id == user_id)
            if session_id:
                where.append(QuestionModel.session_id == session_id)
            if project_id:
                where.append(QuestionModel.project_id == project_id)
            if type:
                normalised_type = type.strip().lower()
                if normalised_type not in {"mcq", "multiple_response", "true_false"}:
                    raise HTTPException(status_code=400, detail="Unsupported type filter. Use 'mcq' or 'multiple_response'.")
                where.append(QuestionModel.type == normalised_type)
            if hasVariants is not None:
                variant_exists = select(VariantModel.id).where(VariantModel.question_id == QuestionModel.id).limit(1).exists()
                if hasVariants:
                    where.append(variant_exists)
                else:
                    where.append(~variant_exists)
            if isApproved is not None:
                where.append(QuestionModel.isApproved == isApproved)
            if isArchived is not None:
                where.append(QuestionModel.isArchived == isArchived)
            if q:
                where.append(QuestionModel.question_text.ilike(f"%{q}%"))

            if where:
                stmt = stmt.where(*where)

            # Count
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = db.execute(count_stmt).scalar_one()

            # Sort
            sort_col = getattr(QuestionModel, sort, QuestionModel.updated_at)
            if order.lower() == "desc":
                sort_col = sort_col.desc()
            stmt = stmt.order_by(sort_col)

            # Pagination
            offset = (page - 1) * pageSize
            stmt = stmt.offset(offset).limit(pageSize)

            # Base questions
            questions = list(db.execute(stmt).scalars())

            # Fetch variants in one shot
            id_list = [q.id for q in questions]
            variants_by_qid: dict[str, list[VariantModel]] = {}
            if id_list:
                v_stmt = select(VariantModel).where(VariantModel.question_id.in_(id_list))
                variant_rows = list(db.execute(v_stmt).scalars())
                for v in variant_rows:
                    variants_by_qid.setdefault(v.question_id, []).append(v)
            
            # Build payloads with variants
            out_items: List[QuestionOut] = []
            for qobj in questions:
                variants = [
                    QuestionVariantOut.model_validate(v)
                    for v in variants_by_qid.get(qobj.id, [])
                ]
                item = QuestionOut.model_validate(qobj)
                item.variants = variants
                out_items.append(item)

            return ListOut(
                total=total,
                page=page,
                pageSize=pageSize,
                questions=out_items,
            )
        except Exception as e:
            trace_exception(e)
            raise HTTPException(status_code=500, detail=f"Failed to list questions: {e}")

    # --- GET /v1/questions/{id} (read)
    @router.get("/{id}", response_model=ItemOut, dependencies=[Depends(auth)])
    def get_question(id: str = Path(...), db: Session = Depends(get_db)):
        try:
            obj = db.get(QuestionModel, id)
            if not obj:
                raise HTTPException(status_code=404, detail="Question not found.")

            # Fetch all variants for this question
            v_stmt = select(VariantModel).where(VariantModel.question_id == id)
            variant_rows = list(db.execute(v_stmt).scalars())
            variants = [QuestionVariantOut.model_validate(v) for v in variant_rows]

            out = QuestionOut.model_validate(obj)
            out.variants = variants
            return ItemOut(question=out)
        except HTTPException:
            raise
        except Exception as e:
            trace_exception(e)
            raise HTTPException(status_code=500, detail=f"Failed to fetch question: {e}")

    # --- PATCH /v1/questions/{id} (partial update incl. approve/archive/unapprove/unarchive)
    @router.patch("/{id}", response_model=SuccessOut, dependencies=[Depends(auth)])
    def patch_question(
        id: str,
        payload: PatchQuestionIn,
        db: Session = Depends(get_db),
    ):
        try:
            updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update.")
            stmt = (
                update(QuestionModel)
                .where(QuestionModel.id == id)
                .values(**updates)
            )
            res = db.execute(stmt)
            db.commit()
            if (res.rowcount or 0) == 0:
                raise HTTPException(status_code=404, detail="Question not found or no changes.")
            return SuccessOut(message="Question updated.")
        except HTTPException:
            raise
        except Exception as e:
            trace_exception(e)
            raise HTTPException(status_code=500, detail=f"Failed to update question: {e}")

    # --- DELETE /v1/questions/{id} (soft delete → isArchived=true)
    @router.delete("/{id}", response_model=SuccessOut, dependencies=[Depends(auth)])
    def delete_question(id: str, db: Session = Depends(get_db)):
        try:
            stmt = (
                update(QuestionModel)
                .where(QuestionModel.id == id)
                .values(isArchived=True)
            )
            res = db.execute(stmt)
            db.commit()
            if (res.rowcount or 0) == 0:
                raise HTTPException(status_code=404, detail="Question not found.")
            return SuccessOut(message="Question archived.")
        except HTTPException:
            raise
        except Exception as e:
            trace_exception(e)
            raise HTTPException(status_code=500, detail=f"Failed to archive question: {e}")

    # --- PATCH /v1/questions (bulk update via { ids, patch })
    @router.patch("/", response_model=SuccessOut, dependencies=[Depends(auth)])
    def bulk_patch(
        body: BulkPatchIn,
        db: Session = Depends(get_db),
    ):
        try:
            if not body.ids:
                raise HTTPException(status_code=400, detail="ids cannot be empty.")
            patch = body.patch.model_dump(exclude_none=True)
            if not patch:
                raise HTTPException(status_code=400, detail="patch cannot be empty.")
            stmt = (
                update(QuestionModel)
                .where(QuestionModel.id.in_(body.ids))
                .values(**patch)
            )
            res = db.execute(stmt)
            db.commit()
            if (res.rowcount or 0) == 0:
                raise HTTPException(status_code=404, detail="No matching questions updated.")
            return SuccessOut(message=f"Updated {res.rowcount} question(s).")
        except HTTPException:
            raise
        except Exception as e:
            trace_exception(e)
            raise HTTPException(status_code=500, detail=f"Bulk update failed: {e}")
    
    @router.post("/export", dependencies=[Depends(auth)])
    async def export_questions(payload: ExportQuestionsIn):
        try:
            # Generate file bytes
            result = await export_questions_controller(payload)
            fileformat = result["fileformat"]
            filedata_b64 = result["filedata"]

            # Decode base64 → bytes
            file_bytes = base64.b64decode(filedata_b64)

            # Define MIME type and file extension
            if fileformat == "csv":
                media_type = "text/csv; charset=utf-8"
                ext = "csv"
            elif fileformat == "qti":
                media_type = "application/zip"
                ext = "zip"
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format.")

            filename = f"{payload.filename}.{ext}"

            # Return a binary StreamingResponse that triggers download
            headers = {
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }

            return StreamingResponse(io.BytesIO(file_bytes), media_type=media_type, headers=headers)

        except HTTPException:
            raise
        except Exception as e:
            trace_exception(e)
            raise HTTPException(status_code=500, detail=f"Export failed: {e}")
    
    return router
