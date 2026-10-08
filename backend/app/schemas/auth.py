from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value):
        if not value.strip():
            raise ValueError("Name must not be blank")
        return value.strip()


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class RegisterResponse(BaseModel):
    patient_id: str
    message: str = "Patient registered successfully."


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PatientResponse(BaseModel):
    patient_id: str
    name: str
    email: str
    role: str = "patient"
