-- CreateEnum
CREATE TYPE "DocStatus" AS ENUM ('uploaded', 'evaluating', 'evaluated', 'failed');

-- CreateTable
CREATE TABLE "documents" (
    "document_id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "application_id" UUID,
    "original_name" TEXT NOT NULL,
    "storage_key" TEXT NOT NULL,
    "sha256" TEXT NOT NULL,
    "size_bytes" INTEGER NOT NULL,
    "status" "DocStatus" NOT NULL DEFAULT 'uploaded',
    "uploaded_by" UUID,
    "mongo_ai_evaluation_ref" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "documents_pkey" PRIMARY KEY ("document_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "documents_storage_key_key" ON "documents"("storage_key");

-- CreateIndex
CREATE INDEX "documents_application_id_idx" ON "documents"("application_id");

-- AddForeignKey
ALTER TABLE "documents" ADD CONSTRAINT "documents_application_id_fkey" FOREIGN KEY ("application_id") REFERENCES "applications"("application_id") ON DELETE CASCADE ON UPDATE CASCADE;
