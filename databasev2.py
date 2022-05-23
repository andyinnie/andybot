# databasev2.py
# use local file storage rather than discord channels
# that was a neat idea but it was slow and also async

DB_DIR = 'database/'


def load(core):
    class Table:
        def __init__(self, table_name):
            self.name = table_name
            self.file_name = DB_DIR + self.name + '.csv'
            self.rows = list()  # tuple of dicts; keys are table headers
            self.headers = tuple()  # tuple of strings
            self.read_in()

        def insert(self, data: list):
            if not data:
                return
            self.read_in()
            self.rows.append({
                self.headers[i]: data[i]
                for i in range(len(self.headers))
            })
            self.write_out()

        def select(self, where: callable, limit: int = None):
            self.read_in()
            return_list = []
            for row in self.rows:
                if where(row):
                    return_list.append(row)
                    if limit is not None and limit <= len(return_list):
                        break
            return tuple(return_list)

        def update_or_insert(self, where: callable, update_values: dict, insert_values=None):
            self.read_in()
            updated = False
            for row in self.rows:
                if where(row):
                    row.update(update_values)
                    updated = True

            if updated:
                self.write_out()
            else:  # let insert() handle writing out
                self.insert(insert_values)

        def read_in(self):
            with open(self.file_name, 'r') as f:
                lines = f.read().split('\n')
                lines = [l.strip() for l in lines if l]
                header_line = lines.pop(0)
                headers = tuple(header_line.split(','))
                self.headers = headers
                self.rows = list()
                for line in lines:
                    self.rows.append({
                        headers[i]: line.split(',')[i]
                        for i in range(len(headers))
                    })

        def write_out(self):
            if self.rows:
                headers = self.rows[0].keys()
                with open(self.file_name, 'w') as f:
                    f.writelines([','.join(headers) + '\n'] + [
                        ','.join([
                            str(val) for val in row.values()
                        ]) + '\n'
                        for row in self.rows
                    ])

    class DBExport:
        @staticmethod
        def get_table(name):
            return Table(name)

    core.exports.put('database', DBExport)
    print('Exported database')
