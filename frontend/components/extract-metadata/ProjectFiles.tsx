import React, { useState } from "react";
import { PdfFile } from "../../utils/utils";
import {
  FileText,
  Download,
  AlertCircle,
  FileText as FilePdf,
  Eye,
  Trash2,
} from "lucide-react";
import setupBaseUrl from "../../utils/setupBaseUrl";
import {
  MessageManagerContext,
  Modal,
  Button,
  DropFiles,
} from "@defogdotai/agents-ui-components/core-ui";

interface ProjectFilesProps {
  files: PdfFile[];
  token: string;
  dbName: string;
  onFilesUploaded?: (dbName: string, dbInfo: any) => void;
}

const ProjectFiles: React.FC<ProjectFilesProps> = ({
  files,
  token,
  dbName,
  onFilesUploaded,
}) => {
  const [uploading, setUploading] = useState(false);
  const [deletingFileId, setDeletingFileId] = useState<number | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const message = React.useContext(MessageManagerContext);

  const handleDownload = (fileId: number) => {
    // Create download URL and open in new tab
    const downloadUrl = setupBaseUrl("http", `download_pdf/${fileId}`);
    window.open(downloadUrl, "_blank");
  };

  const handleDeleteClick = (file: PdfFile) => {
    setDeletingFileId(file.file_id);
    setShowDeleteConfirm(true);
  };

  const handleDelete = async () => {
    if (!deletingFileId) return;

    try {
      const response = await fetch(
        setupBaseUrl(
          "http",
          `delete_pdf/${deletingFileId}?token=${token}&db_name=${dbName}`
        ),
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to delete file");
      }

      const data = await response.json();
      message.success("File deleted successfully");

      // Close modals
      setShowDeleteConfirm(false);
      setDeletingFileId(null);

      // Update the parent component with the updated project info
      if (onFilesUploaded) {
        onFilesUploaded(dbName, data.db_info);
      }
    } catch (error) {
      console.error("Error deleting file:", error);
      message.error("Failed to delete file");
    }
  };

  // This is the new simplified upload function that just takes files directly
  const uploadFiles = async (files: File[]) => {
    if (!dbName) {
      message.error("No project selected");
      return;
    }

    if (files.length === 0) {
      message.info("No files selected for upload");
      return;
    }

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("token", token);
      formData.append("db_name", dbName);

      files.forEach((file) => {
        formData.append("files", file);
      });

      const response = await fetch(setupBaseUrl("http", "upload_files"), {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to upload files");
      }

      const data = await response.json();
      message.success("Files uploaded successfully");

      if (onFilesUploaded) {
        onFilesUploaded(dbName, data.db_info);
      }
    } catch (error) {
      console.error("Error uploading files:", error);
      message.error("Failed to upload files");
    } finally {
      setUploading(false);
    }
  };

  const getFileIcon = (fileName: string) => {
    if (fileName.toLowerCase().endsWith(".pdf")) {
      return <FilePdf className="w-6 h-6 text-blue-500" />;
    }
    return <FileText className="w-6 h-6 text-blue-500" />;
  };

  return (
    <div className="prose dark:prose-invert max-w-none mb-6">
      <h3>Project Files</h3>
      <p>
        Upload PDF documents to provide additional context for your queries and
        reports. These files can be used as reference materials when generating
        reports or answering complex questions about your data.
      </p>

      <DropFiles
        onFileSelect={(e, files) => {
          // With our updated component, we'll receive the valid files directly
          if (files.length === 0) return;
          uploadFiles(files);
        }}
        onDrop={(e, files) => {
          // With our updated component, we'll receive the valid files directly
          if (files.length === 0) return;
          uploadFiles(files);
        }}
        onInvalidFiles={(e, invalidFiles, errorMessage) => {
          // Display error for invalid files
          message.error(errorMessage);
        }}
        acceptedFileTypes={[".pdf"]}
        allowMultiple={true}
        disabled={uploading}
        showIcon={true}
        selectedFiles={[]}
        label="Drag & drop PDF files here or click to browse"
        rootClassNames="mb-6"
      />

      <h4>Your files</h4>

      {files && files.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {files.map((file) => (
            <div
              key={file.file_id}
              className="border rounded-lg p-4 flex flex-col bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex items-center mb-3">
                {getFileIcon(file.file_name)}
                <span className="ml-2 font-medium truncate">
                  {file.file_name}
                </span>
              </div>

              <div className="mt-auto pt-3 flex justify-end gap-2">
                <Button
                  variant="secondary"
                  onClick={() => handleDownload(file.file_id)}
                  title="Download file"
                >
                  <Download className="w-4 h-4 mr-1" />
                  Download
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => handleDeleteClick(file)}
                  title="Delete file"
                  className="bg-gray-100 hover:bg-red-100 dark:bg-gray-700 dark:hover:bg-red-900/30 group"
                >
                  <Trash2 className="w-4 h-4 text-gray-600 group-hover:text-red-600 dark:text-gray-300 dark:group-hover:text-red-400" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
          <AlertCircle className="w-10 h-10 mb-3 text-gray-400" />
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            No files associated with this project.
          </p>
          <p className="text-gray-400 dark:text-gray-500 text-xs mt-1">
            Upload PDF files above.
          </p>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        open={showDeleteConfirm}
        onCancel={() => {
          setShowDeleteConfirm(false);
          setDeletingFileId(null);
        }}
        title="Confirm Deletion"
        contentClassNames="w-full max-w-md"
        footer={
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={handleDelete}
              className="bg-gray-200 hover:bg-red-100 dark:bg-gray-700 dark:hover:bg-red-900/30 group"
            >
              <Trash2 className="w-4 h-4 mr-2 group-hover:text-red-600 dark:group-hover:text-red-400" />
              Delete
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setShowDeleteConfirm(false);
                setDeletingFileId(null);
              }}
            >
              Cancel
            </Button>
          </div>
        }
      >
        <div className="p-4">
          <div className="flex items-center mb-4">
            <AlertCircle className="w-8 h-8 mr-2 text-red-500" />
            <h3 className="text-lg font-semibold">Delete PDF File</h3>
          </div>
          <p>
            Are you sure you want to delete this file? This action cannot be
            undone.
          </p>
          <p className="mt-2 text-sm text-gray-500">
            Deleting this file will remove it from the project and all
            references to it.
          </p>
        </div>
      </Modal>
    </div>
  );
};

export default ProjectFiles;
