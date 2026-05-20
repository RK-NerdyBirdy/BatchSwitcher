import csv
import io
from pydantic import ValidationError, BaseModel, Field, EmailStr


class StudentBatchAssignmentRow(BaseModel):
    """Schema for CSV row with batch assignment."""
    register_number: str = Field(..., max_length=20)
    student_name: str = Field(..., max_length=100)
    email: EmailStr
    phone_number: str | None = Field(default=None, max_length=15)
    semester_name: str = Field(..., max_length=100)
    batch_name: str = Field(..., max_length=50)
    cgpa: float = Field(..., ge=0, le=10)


class CSVParsingError(Exception):
    def __init__(self, row_number: int, message: str):
        self.row_number = row_number
        self.message = message
        super().__init__(f"Row {row_number}: {message}")


class CSVService:
    """Service for parsing and validating student CSV uploads with batch assignment."""

    REQUIRED_COLUMNS = {
        "register_number",
        "student_name",
        "email",
        "semester_name",
        "batch_name",
        "cgpa",
    }
    OPTIONAL_COLUMNS = {"phone_number"}

    @staticmethod
    async def parse_csv(file_content: bytes) -> list[StudentBatchAssignmentRow]:
        """Parse CSV file into student records with batch assignments.

        Expected CSV format:
            register_number,student_name,email,phone_number,cgpa,batch_name,semester_name

        Returns:
            List of validated StudentBatchAssignmentRow objects.

        Raises:
            CSVParsingError: On parsing or validation failures.
        """
        try:
            text = file_content.decode("utf-8")
        except UnicodeDecodeError:
            raise CSVParsingError(0, "File must be UTF-8 encoded")

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise CSVParsingError(0, "CSV is empty or malformed")

        fieldnames_set = set(reader.fieldnames)
        if not CSVService.REQUIRED_COLUMNS.issubset(fieldnames_set):
            missing = CSVService.REQUIRED_COLUMNS - fieldnames_set
            raise CSVParsingError(0, f"Missing required columns: {', '.join(missing)}")

        records: list[StudentBatchAssignmentRow] = []
        for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            row_clean = {k: (v.strip() if v else None) for k, v in row.items()}

            # Validate required fields not empty
            if not row_clean.get("register_number"):
                raise CSVParsingError(row_num, "register_number cannot be empty")
            if not row_clean.get("student_name"):
                raise CSVParsingError(row_num, "student_name cannot be empty")
            if not row_clean.get("email"):
                raise CSVParsingError(row_num, "email cannot be empty")
            if not row_clean.get("semester_name"):
                raise CSVParsingError(row_num, "semester_name cannot be empty")
            if not row_clean.get("batch_name"):
                raise CSVParsingError(row_num, "batch_name cannot be empty")
            if not row_clean.get("cgpa"):
                raise CSVParsingError(row_num, "cgpa cannot be empty")

            try:
                record = StudentBatchAssignmentRow(
                    register_number=row_clean["register_number"],
                    student_name=row_clean["student_name"],
                    email=row_clean["email"],
                    phone_number=row_clean.get("phone_number"),
                    semester_name=row_clean["semester_name"],
                    batch_name=row_clean["batch_name"],
                    cgpa=float(row_clean["cgpa"]),
                )
                records.append(record)
            except ValueError as e:
                raise CSVParsingError(row_num, f"Invalid data type: {str(e)}")
            except ValidationError as e:
                errors = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
                raise CSVParsingError(row_num, f"Validation failed: {errors}")

        return records


csv_service = CSVService()
