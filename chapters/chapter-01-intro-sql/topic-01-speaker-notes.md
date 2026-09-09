# Chapter 1 Speaker Notes

## Working with SQL in SQLite

Direct database work before Python or web interfaces. SQLite is the database engine; sqlite3 is the command-line program. Source: chapter-01-intro-sql.md and ../../topic-01-intro-sql/example.txt. Transcript excerpts preserve the session; the SQL examples on these slides use cleaner line breaks for readability.

## A Fresh Practice Database

The repository's pets.db already contains records. A fresh practice directory makes the creation sequence reproducible. Use another directory name for another fresh run. pwd reports the working directory. The relative name pets.db can refer to different files in different directories. Version banners may differ from the transcript.

## Which Program Reads the Command?

Continuation prompts mean the statement is unfinished. Dot commands occupy their own lines without semicolons. SQL statements can span lines and end with semicolons in this session. The command is sqlite3, not sqlite. Shell reference: https://sqlite.org/cli.html.

## Inspecting the Database

The initial database has no application tables. .schema shows definitions; .tables lists tables. The last two commands control result presentation. Display settings do not change the pet records. Source: ../../topic-01-intro-sql/example.txt.

## Creating the Pet Table

Named columns describe the records. NULL represents a missing value; name and kind cannot be NULL. NOT NULL does not reject an empty string. SQLite supplies omitted integer identifiers. INTEGER PRIMARY KEY already supports automatic identifiers. AUTOINCREMENT adds a nonreuse rule for identifiers from committed rows; SQLite maintains sqlite_sequence. .tables and .schema confirm the definition. Reference: https://sqlite.org/autoinc.html.

## Inserting Dorothy

Column and value positions correspond. Text in single quotes; age is numeric. The insert omits id, so SQLite supplies 1 in the fresh practice database. The transcript first uses VALUE and gets a syntax error. VALUES is the keyword even for one row.

## Reading the Pets

Setup commands after Dorothy:
INSERT INTO pet (name, kind, age, food) VALUES ('Sandy', 'cat', 11, 'tuna');
INSERT INTO pet (name, kind, age, food) VALUES ('Whiskers', 'hamster', 11, 'hamster chow');
The asterisk requests all columns. FROM names the table. SELECT reads the current records without changing them. Display order follows the transcript here; guaranteed ordering requires ORDER BY.

## Choosing Columns and Rows

SELECT names the returned columns. WHERE supplies the row condition. The transcript's failed SELECT FROM pet WHERE kind = 'cat' omits the selection list. SELECT * fixes it. SQLite accepts == too; use = in these examples. Exact equality against 'Do' does not match 'Dorothy'. No matches is a valid empty result.

## Deleting the Cats

Inspect the matching rows before deleting. DELETE applies to every cat; Sandy is the only cat in this data. Without WHERE, DELETE removes all rows. Identifiers do not get renumbered. SELECT kind, food FROM pet WHERE age = 11 still returns Dorothy and Whiskers, since both have age 11.

## A Query from the Shell

Double quotes keep the SQL together as a shell argument. Single quotes delimit the SQL string. The backslash continues the shell command onto the next line. -header -column requests readable output for this invocation. The process that created the records has exited, but this new process can still retrieve them.

## Several Lines of Shell Input

A shell here-document feeds several lines to sqlite3. SQL is the chosen delimiter, not an SQL keyword in that position. Quoting the opening delimiter suppresses shell variable expansion and command substitution. Closing delimiter alone on its line, without quotes. The transcript uses this technique after first trying the wrong executable name.

## Restoring Sandy for the Sorting Examples

Sandy appears in the later sorting output although the transcript previously deleted her. The chapter adds this restoration to make the sequence reproducible. Explicit id 2 restores the original row. Run this once after the deletion. This command is an added step, not a quotation from the transcript.

## Sorting the Result

ORDER BY kind gives cat, dog, hamster. ORDER BY food gives hamster chow, peanut butter, tuna: Whiskers, Dorothy, Sandy. Sorting controls the returned result without changing record identifiers. Without ORDER BY, the observed order is not a guarantee.
