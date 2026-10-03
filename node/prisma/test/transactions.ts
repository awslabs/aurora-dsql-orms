/**
 * Statements inside each BEGIN...COMMIT block of transformed SQL. Fails if any
 * statement sits outside a block or a block holds anything but one statement,
 * because Prisma can run the whole file as one implicit transaction.
 */
export function transactionBlocks(sql: string): string[] {
  const blocks: string[] = [];
  const outside = sql.replace(
    /^BEGIN;\s*([\s\S]*?)\s*^COMMIT;$/gm,
    (_match, body: string) => {
      blocks.push(body);
      return "";
    },
  );
  expect(outside.trim()).toBe("");
  for (const body of blocks) {
    // dsql-lint ends every statement it writes with `;` at the end of a line.
    expect(body.match(/;$/gm)).toHaveLength(1);
    expect(body.endsWith(";")).toBe(true);
  }
  return blocks;
}
