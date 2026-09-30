-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('applicant', 'evaluator', 'admin');

-- CreateEnum
CREATE TYPE "AppStatus" AS ENUM ('draft', 'submitted', 'under_review', 'returned_for_correction', 'approved', 'rejected');

-- CreateEnum
CREATE TYPE "ApplicationType" AS ENUM ('new_institution', 'extension_of_approval', 'new_program', 'increase_in_intake', 'closure', 'hibernation');

-- CreateTable
CREATE TABLE "users" (
    "user_id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "full_name" TEXT NOT NULL,
    "phone" TEXT,
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "role" "UserRole" NOT NULL DEFAULT 'applicant',
    "institution_id" UUID,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "institutions" (
    "institution_id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "parent_institution_id" UUID,
    "name" TEXT NOT NULL,
    "primary_contact_user_id" UUID,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "institutions_pkey" PRIMARY KEY ("institution_id")
);

-- CreateTable
CREATE TABLE "applications" (
    "application_id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "application_type" "ApplicationType" NOT NULL,
    "institution_id" UUID NOT NULL,
    "academic_year" TEXT NOT NULL,
    "current_status" "AppStatus" NOT NULL DEFAULT 'draft',
    "mongo_application_ref" TEXT,
    "submitted_by" UUID,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "applications_pkey" PRIMARY KEY ("application_id")
);

-- CreateTable
CREATE TABLE "application_status_logs" (
    "log_id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "application_id" UUID NOT NULL,
    "old_status" "AppStatus",
    "new_status" "AppStatus" NOT NULL,
    "changed_by" UUID,
    "mongo_ai_evaluation_ref" TEXT,
    "changed_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "application_status_logs_pkey" PRIMARY KEY ("log_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "applications_institution_id_idx" ON "applications"("institution_id");

-- CreateIndex
CREATE UNIQUE INDEX "applications_institution_id_academic_year_application_type_key" ON "applications"("institution_id", "academic_year", "application_type");

-- CreateIndex
CREATE INDEX "application_status_logs_application_id_idx" ON "application_status_logs"("application_id");

-- AddForeignKey
ALTER TABLE "users" ADD CONSTRAINT "users_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "institutions"("institution_id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "institutions" ADD CONSTRAINT "institutions_parent_institution_id_fkey" FOREIGN KEY ("parent_institution_id") REFERENCES "institutions"("institution_id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "institutions" ADD CONSTRAINT "institutions_primary_contact_user_id_fkey" FOREIGN KEY ("primary_contact_user_id") REFERENCES "users"("user_id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "applications" ADD CONSTRAINT "applications_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "institutions"("institution_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "applications" ADD CONSTRAINT "applications_submitted_by_fkey" FOREIGN KEY ("submitted_by") REFERENCES "users"("user_id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "application_status_logs" ADD CONSTRAINT "application_status_logs_application_id_fkey" FOREIGN KEY ("application_id") REFERENCES "applications"("application_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "application_status_logs" ADD CONSTRAINT "application_status_logs_changed_by_fkey" FOREIGN KEY ("changed_by") REFERENCES "users"("user_id") ON DELETE SET NULL ON UPDATE CASCADE;
