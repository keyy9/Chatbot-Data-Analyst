import React from "react";

interface DataTableProps {
  headers: React.ReactNode;
  children: React.ReactNode;
}

export const DataTable: React.FC<DataTableProps> = ({ headers, children }) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          {headers}
        </thead>
        <tbody className="divide-y divide-border/40 text-xs">
          {children}
        </tbody>
      </table>
    </div>
  );
};
