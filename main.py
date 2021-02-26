class Reader:
    def __init__(self, input_file_name):
        self.n_intersections = 0
        self.n_streets = 0
        self.n_cars = 0

        self.cars = []
        self.intersections = []
        self.streets = []
        self.street_name_id_pairs = {}
        self.street_intersection_pairs = {}

        self.all_street_scores = {}

        self.input_path_prefix = './input/'
        self.output_path_prefix = './output/'
        self.input_file_name = input_file_name
        self.read_input()

    def read_input(self):
        with open(self.input_path_prefix + self.input_file_name) as input_file:
            header_line = input_file.readline()
            _, self.n_intersections, self.n_streets, self.n_cars, _ = [
                int(i) for i in header_line.strip().split()
            ]

            self.initialize_intersections()
            self.read_streets(input_file)
            self.read_cars(input_file)

    def initialize_intersections(self):
        for i in range(self.n_intersections):
            self.intersections.append({
                'id': i,
                'in': [],
                'in_scores': {},
                'out': [],
                'schedule': {}
            })

    def read_streets(self, input_file):
        for i in range(self.n_streets):
            street_line = input_file.readline()
            i_start, i_end, s_name, s_len = street_line.strip().split()

            self.streets.append({
                'id': i,
                'name': s_name,
                'len': int(s_len),
                'i_start': int(i_start),
                'i_end': int(i_end),
            })
            self.street_name_id_pairs[s_name] = i
            self.street_intersection_pairs[i] = int(i_end)

            self.intersections[int(i_start)]['out'].append(i)
            self.intersections[int(i_end)]['in'].append(i)

    def read_cars(self, input_file):
        for i in range(self.n_cars):
            car_line = input_file.readline()
            car_line_fragments = car_line.strip().split()

            self.cars.append({
                'i_start': int(car_line_fragments.pop(0)),
                'route_table': [self.street_name_id_pairs[s_name] for s_name in car_line_fragments]
            })

    def write_output(self):
        with open(self.output_path_prefix + self.input_file_name, 'w+') as file:
            file.write(str(self.n_intersections) + "\n")
            for i in range(self.n_intersections):
                file.write(str(i) + '\n')
                if len(self.intersections[i]['in']):
                    sorted_schedules = list(
                        sorted(self.intersections[i]['schedule'].items(), key=lambda item: item[1], reverse=True))

                    n_schedules = len(sorted_schedules)
                    file.write(str(n_schedules) + '\n')

                    for in_street_name, seconds in sorted_schedules:
                        file.write(in_street_name + ' ' + str(seconds) + '\n')


class Solver(Reader):
    def solve(self, min_scheduled_time, max_scheduled_time,
              upscale_fraction=10, upscale_factor=2, use_round_instead_of_floor=False):
        self.set_schedules(upscale_fraction, upscale_factor)
        self.normalize_schedules(min_scheduled_time, max_scheduled_time, use_round_instead_of_floor)
        self.write_output()

        print('Solved: ' + self.input_file_name)

    def set_schedules(self, upscale_fraction, upscale_factor):
        self.score_streets_in_intersections()
        self.schedule_one_way_in_intersections()
        self.schedule_round_robin()
        self.upscale_fraction_of_best_streets(upscale_fraction, upscale_factor)

    def schedule_one_way_in_intersections(self):
        for i in range(self.n_intersections):
            if len(self.intersections[i]['in']) == 1:
                in_street_id = self.intersections[i]['in'][0]
                in_street_name = self.streets[in_street_id]['name']
                self.intersections[i]['schedule'] = {
                    in_street_name: 1
                }

    def score_streets_in_intersections(self):
        for car_id in range(self.n_cars):
            streets_to_score = self.cars[car_id]['route_table'][:-1]
            n_streets_to_score = len(streets_to_score)
            if n_streets_to_score == 0:
                continue

            for loop_id, street_id in enumerate(streets_to_score):
                i_end = self.street_intersection_pairs[street_id]
                if street_id not in self.intersections[i_end]['in_scores']:
                    self.intersections[i_end]['in_scores'][street_id] = 0
                self.intersections[i_end]['in_scores'][street_id] += 1
                self.increase_street_global_score(street_id, loop_id, n_streets_to_score)

    def increase_street_global_score(self, street_id, loop_id, n_streets_to_score):
        if street_id not in self.all_street_scores:
            self.all_street_scores[street_id] = {
                'id': street_id,
                'score': 0
            }
        self.all_street_scores[street_id]['score'] += int(
            ((n_streets_to_score - loop_id) / n_streets_to_score) * 2 + 1)
        if loop_id == 0:
            self.all_street_scores[street_id]['score'] += 3

    def schedule_round_robin(self):
        for i in range(self.n_intersections):
            if len(self.intersections[i]['schedule']) == 0:
                if len(self.intersections[i]['in_scores']) > 0:
                    for in_street_id in self.intersections[i]['in_scores']:
                        in_street_name = self.streets[in_street_id]['name']
                        self.intersections[i]['schedule'][in_street_name] = self.intersections[i]['in_scores'][
                            in_street_id]
                else:
                    for in_street_id in self.intersections[i]['in']:
                        in_street_name = self.streets[in_street_id]['name']
                        self.intersections[i]['schedule'][in_street_name] = 1

    def upscale_fraction_of_best_streets(self, suggested_fraction_of_streets, upscale_factor):
        n_upscaled_streets = int(self.n_streets / suggested_fraction_of_streets)
        if n_upscaled_streets == 0:
            return

        sorted_global_street_scores = list(
            sorted(self.all_street_scores.items(), key=lambda item: item[1]['score'], reverse=True))
        streets_to_increase_score = sorted_global_street_scores[:n_upscaled_streets]

        for street_id, global_street_score in streets_to_increase_score:
            if global_street_score == 0:
                continue

            i_end = self.streets[street_id]['i_end']
            in_street_name = self.streets[street_id]['name']
            self.intersections[i_end]['schedule'][in_street_name] *= upscale_factor

    def normalize_schedules(self, min_scheduled_time, max_scheduled_time, use_round_instead_of_floor):
        for i in range(self.n_intersections):
            if len(self.intersections[i]['in']):
                min_seconds, max_seconds = self.get_min_max_scheduled_seconds(i)

                for street_name, seconds in self.intersections[i]['schedule'].items():
                    normalized_seconds = self.get_normalized_seconds(seconds, min_seconds, max_seconds,
                                                                     min_scheduled_time, max_scheduled_time)
                    normalized_seconds = self.get_rounded_seconds(normalized_seconds, use_round_instead_of_floor)
                    self.intersections[i]['schedule'][street_name] = normalized_seconds

    def get_min_max_scheduled_seconds(self, intersection_id):
        min_seconds, max_seconds = None, None

        for street_name, seconds in self.intersections[intersection_id]['schedule'].items():
            if min_seconds is None or seconds < min_seconds:
                min_seconds = seconds
            if max_seconds is None or seconds > max_seconds:
                max_seconds = seconds

        if max_seconds == min_seconds:
            min_seconds = max_seconds - 1

        return min_seconds, max_seconds

    def get_normalized_seconds(self, seconds, min_seconds, max_seconds, min_scheduled_time, max_scheduled_time):
        scale_factor = max_scheduled_time - min_scheduled_time

        normalized_seconds = ((seconds - min_seconds) / (max_seconds - min_seconds)) * scale_factor
        normalized_seconds += min_scheduled_time

        return normalized_seconds

    def get_rounded_seconds(self, seconds, use_round_instead_of_floor):
        if use_round_instead_of_floor:
            return round(seconds)
        return int(seconds)


if __name__ == '__main__':
    Solver('a.txt').solve(1, 2)
    Solver('b.txt').solve(1, 1)
    Solver('c.txt').solve(1, 2)
    Solver('d.txt').solve(1, 1)
    Solver('e.txt').solve(1, 4, use_round_instead_of_floor=True)
    Solver('f.txt').solve(1, 6, upscale_fraction=10, upscale_factor=1000)
