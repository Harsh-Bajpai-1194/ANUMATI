import mongoose from 'mongoose';

const dynamicApplicationFormSchema = new mongoose.Schema({
    // Maps back to PostgreSQL `applications.application_id` (stored as a stringified UUID)
    applicationId: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },

    // Type of application to know how to validate or render the form schema
    applicationType: {
      type: String,
      required: true,
      index: true,
    },

    // Flexible storage for dynamic form sections, questions, and answers
    // Example: { "infrastructure": { "totalAreaAcres": 10, "classroomsCount": 25 }, "courses": [...] }
    formData: {
      type: mongoose.Schema.Types.Mixed,
      required: true,
      default: {},
    },
  },
  {
    timestamps: true, // Automatically manages createdAt and updatedAt
    collection: 'application_details',
  }
);

const DynamicApplicationForm = mongoose.model('DynamicApplicationForm', dynamicApplicationFormSchema);
export default DynamicApplicationForm;